# Worker (Compute Engine GPU)

Long-running GPU worker that:
- pulls job IDs from Pub/Sub
- downloads the uploaded image from GCS
- runs TRELLIS.2 image→3D
- post-processes via `o_voxel.postprocess.to_glb`
- uploads outputs back to GCS
- updates Cloud SQL job status (+ refunds on failure)


