from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass
from typing import Any

import torch
from PIL import Image


@dataclass(frozen=True)
class TrellisResult:
    glb_path: str


def _ensure_vendor_on_path(repo_root: str):
    upstream = os.path.join(repo_root, "vendor", "trellis2_upstream")
    if upstream not in sys.path:
        sys.path.insert(0, upstream)


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

    from trellis2.pipelines import Trellis2ImageTo3DPipeline
    import o_voxel

    pipeline = Trellis2ImageTo3DPipeline.from_pretrained(model_id)
    pipeline.cuda()

    pipeline_type = {512: "512", 1024: "1024_cascade", 1536: "1536_cascade"}[resolution]

    outputs = pipeline.run(
        image,
        seed=seed,
        preprocess_image=True,
        pipeline_type=pipeline_type,
        return_latent=False,
    )
    mesh = outputs[0]
    mesh.simplify(16777216)  # nvdiffrast limit

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

    tmpdir = tempfile.mkdtemp(prefix="solidgen_")
    glb_path = os.path.join(tmpdir, "asset.glb")
    glb_mesh.export(glb_path, extension_webp=True)
    torch.cuda.empty_cache()

    return TrellisResult(glb_path=glb_path)


