from __future__ import annotations

import logging
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Literal

import torch
from PIL import Image


logger = logging.getLogger("solidgen-worker.trellis")


@dataclass(frozen=True)
class TrellisResult:
    glb_path: str


def _ensure_vendor_on_path(repo_root: str):
    upstream = os.path.join(repo_root, "vendor", "trellis2_upstream")
    if upstream not in sys.path:
        sys.path.insert(0, upstream)


def _get_env_image_model_kind() -> str:
    return (os.environ.get("TRELLIS_IMAGE_MODEL_KIND") or "").strip().lower()


def _has_hf_token() -> bool:
    # Common env vars respected by huggingface_hub / transformers
    return bool((os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN") or "").strip())


def _load_trellis_pipeline(model_id: str):
    """
    Load Trellis2 pipeline, but allow overriding / falling back the image feature extractor
    to avoid gated-model failures.
    """
    from trellis2.pipelines.base import Pipeline
    from trellis2.pipelines.trellis2_image_to_3d import Trellis2ImageTo3DPipeline, samplers, rembg
    from trellis2.modules import image_feature_extractor

    pipeline = Pipeline.from_pretrained(model_id)
    new_pipeline = Trellis2ImageTo3DPipeline()
    new_pipeline.__dict__ = pipeline.__dict__
    args = pipeline._pretrained_args

    new_pipeline.sparse_structure_sampler = getattr(samplers, args["sparse_structure_sampler"]["name"])(
        **args["sparse_structure_sampler"]["args"]
    )
    new_pipeline.sparse_structure_sampler_params = args["sparse_structure_sampler"]["params"]

    new_pipeline.shape_slat_sampler = getattr(samplers, args["shape_slat_sampler"]["name"])(**args["shape_slat_sampler"]["args"])
    new_pipeline.shape_slat_sampler_params = args["shape_slat_sampler"]["params"]

    new_pipeline.tex_slat_sampler = getattr(samplers, args["tex_slat_sampler"]["name"])(**args["tex_slat_sampler"]["args"])
    new_pipeline.tex_slat_sampler_params = args["tex_slat_sampler"]["params"]

    new_pipeline.shape_slat_normalization = args["shape_slat_normalization"]
    new_pipeline.tex_slat_normalization = args["tex_slat_normalization"]

    # Image feature extractor selection
    override_model_id = (os.environ.get("TRELLIS_IMAGE_MODEL_ID") or "").strip() or None
    kind = _get_env_image_model_kind()
    explicit_dinov2 = kind in {"dinov2", "dino2"}
    explicit_dinov3 = kind in {"dinov3", "dino3"}
    # Default behavior: prefer DINOv3 if a token is present; otherwise use DINOv2 (public).
    prefer_dinov3 = _has_hf_token()
    if explicit_dinov2:
        prefer_dinov3 = False
    elif explicit_dinov3:
        prefer_dinov3 = True

    def _make_extractor(kind_choice: Literal["dinov2", "dinov3"]):
        if kind_choice == "dinov2":
            # torch.hub model name (public): e.g. dinov2_vitg14
            # If the user explicitly requested dinov2, allow TRELLIS_IMAGE_MODEL_ID to be the dinov2 model name.
            model_name = (
                override_model_id
                if (explicit_dinov2 and override_model_id)
                else os.environ.get("TRELLIS_DINOV2_MODEL", "dinov2_vitg14")
            )
            extractor = image_feature_extractor.DinoV2FeatureExtractor(model_name)
            extractor.image_size = getattr(extractor, "image_size", 512)
            return extractor

        # DINOv3 is HF-hosted and can be gated.
        # If TRELLIS_IMAGE_MODEL_ID is set without explicitly selecting dinov2, interpret it as the DINOv3 model id.
        model_name = override_model_id or args["image_cond_model"]["args"].get("model_name")
        image_size = args["image_cond_model"]["args"].get("image_size", 512)
        extractor = image_feature_extractor.DinoV3FeatureExtractor(model_name, image_size=image_size)
        return extractor

    extractor = None
    if prefer_dinov3:
        try:
            extractor = _make_extractor("dinov3")
            logger.info("Using DINOv3 image extractor: %s", getattr(extractor, "model_name", "dinov3"))
        except Exception as e:
            msg = str(e).lower()
            if "gated repo" in msg or "gatedrepo" in msg or "unauthorized" in msg or "401" in msg or "403" in msg:
                logger.warning("DINOv3 access failed; falling back to DINOv2. err=%s", e)
            else:
                raise

    if extractor is None:
        extractor = _make_extractor("dinov2")
        logger.info("Using DINOv2 image extractor: %s", getattr(extractor, "model_name", "dinov2"))

    new_pipeline.image_cond_model = extractor
    new_pipeline.rembg_model = getattr(rembg, args["rembg_model"]["name"])(**args["rembg_model"]["args"])

    new_pipeline.low_vram = args.get("low_vram", True)
    new_pipeline.default_pipeline_type = args.get("default_pipeline_type", "1024_cascade")
    new_pipeline.pbr_attr_layout = {
        "base_color": slice(0, 3),
        "metallic": slice(3, 4),
        "roughness": slice(4, 5),
        "alpha": slice(5, 6),
    }
    new_pipeline._device = "cpu"

    return new_pipeline


def run_trellis_to_glb(
    *,
    repo_root: str,
    image: Image.Image,
    model_id: str,
    resolution: int,
    seed: int,
    decimation_target: int,
    texture_size: int,
) -> TrellisResult:
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")

    _ensure_vendor_on_path(repo_root)

    import o_voxel

    logger.info(
        "Starting Trellis run (model_id=%s, resolution=%s, seed=%s, decimation_target=%s, texture_size=%s)",
        model_id,
        resolution,
        seed,
        decimation_target,
        texture_size,
    )
    logger.info(
        "Torch CUDA available=%s, torch_cuda=%s, device_count=%s",
        torch.cuda.is_available(),
        getattr(torch.version, "cuda", None),
        torch.cuda.device_count(),
    )
    if torch.cuda.is_available() and torch.cuda.device_count() > 0:
        try:
            name = torch.cuda.get_device_name(0)
            cap = torch.cuda.get_device_capability(0)
            logger.info("CUDA device[0]=%s capability=%s", name, cap)
        except Exception:
            logger.exception("Failed to query CUDA device info")

    t0 = time.time()
    pipeline = _load_trellis_pipeline(model_id)
    logger.info("Loaded Trellis pipeline in %.2fs", time.time() - t0)

    t1 = time.time()
    pipeline.cuda()
    logger.info("Moved pipeline to CUDA in %.2fs", time.time() - t1)

    pipeline_type = {512: "512", 1024: "1024_cascade", 1536: "1536_cascade"}[resolution]

    t2 = time.time()
    outputs = pipeline.run(
        image,
        seed=seed,
        preprocess_image=True,
        pipeline_type=pipeline_type,
        return_latent=False,
    )
    logger.info("Pipeline inference completed in %.2fs", time.time() - t2)
    mesh = outputs[0]
    mesh.simplify(16777216)  # nvdiffrast limit

    t3 = time.time()
    glb_mesh = o_voxel.postprocess.to_glb(
        vertices=mesh.vertices,
        faces=mesh.faces,
        attr_volume=mesh.attrs,
        coords=mesh.coords,
        attr_layout=pipeline.pbr_attr_layout,
        grid_size=resolution,
        aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
        decimation_target=decimation_target,
        texture_size=texture_size,
        remesh=True,
        remesh_band=1,
        remesh_project=0,
        use_tqdm=True,
    )
    logger.info("Postprocess to GLB completed in %.2fs", time.time() - t3)

    tmpdir = tempfile.mkdtemp(prefix="solidgen_")
    glb_path = os.path.join(tmpdir, "asset.glb")
    glb_mesh.export(glb_path, extension_webp=True)
    torch.cuda.empty_cache()
    logger.info("Wrote output GLB: %s", glb_path)

    return TrellisResult(glb_path=glb_path)




