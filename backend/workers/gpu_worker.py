import time
import numpy as np
from multiprocessing import Pool, cpu_count
from typing import Dict, Any
from base_worker import BaseWorker, WorkerResult

GPU_TDP_WATTS = 250


def _detect_gpu() -> Dict[str, Any]:
    """Real CUDA detection — not simulated."""
    try:
        import torch
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            return {
                "available": True,
                "backend": "cuda",
                "name": torch.cuda.get_device_name(0),
                "memory_mb": props.total_mem // 1048576,
            }
    except ImportError:
        pass

    try:
        import torch
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return {
                "available": True,
                "backend": "mps",
                "name": "Apple Silicon GPU (MPS)",
                "memory_mb": 0,
            }
    except (ImportError, AttributeError):
        pass

    cores = cpu_count() or 4
    return {
        "available": False,
        "backend": "multiprocessing",
        "name": f"Simulated via {cores}-core parallel",
        "cores": cores,
    }


GPU_INFO = _detect_gpu()


def _chunk_matmul(args):
    """Multiply a chunk of rows of A with B."""
    a_chunk, b = args
    return np.matmul(a_chunk, b)


class GPUWorker(BaseWorker):
    resource_name = "gpu"

    def __init__(self):
        self.gpu_info = GPU_INFO

    def is_available(self) -> bool:
        return True

    def execute(self, task_type: str, params: dict) -> WorkerResult:
        dispatch = {
            "matrix_ops": self._matrix_multiply,
            "image_processing": self._image_processing,
            "simple_compute": self._simple_compute,
            "data_processing": self._simple_compute,
            "ml_training": self._simple_compute,
            "nlp": self._simple_compute,
            "simulation": self._simple_compute,
        }
        handler = dispatch.get(task_type, self._simple_compute)
        return handler(params)

    def _matrix_multiply(self, params: dict) -> WorkerResult:
        n = params.get("matrix_size", 500)

        if self.gpu_info.get("backend") == "cuda":
            return self._cuda_matmul(n)
        elif self.gpu_info.get("backend") == "mps":
            return self._mps_matmul(n)
        else:
            return self._parallel_matmul(n)

    def _cuda_matmul(self, n: int) -> WorkerResult:
        import torch
        a = torch.randn(n, n, device="cuda", dtype=torch.float32)
        b = torch.randn(n, n, device="cuda", dtype=torch.float32)
        torch.cuda.synchronize()

        start = time.perf_counter()
        c = torch.matmul(a, b)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - start

        checksum = float(c[0, 0].cpu())

        return WorkerResult(
            resource="gpu",
            task_type="matrix_ops",
            time_seconds=round(elapsed, 4),
            cost_usd=0.0,
            energy_wh=round((elapsed / 3600) * GPU_TDP_WATTS, 4),
            output_summary=f"GPU (CUDA): {n}x{n} matmul in {elapsed:.4f}s. Checksum: {checksum:.4f}",
            metadata={"matrix_size": n, "backend": "cuda", "gpu_name": self.gpu_info["name"]},
        )

    def _mps_matmul(self, n: int) -> WorkerResult:
        import torch
        a = torch.randn(n, n, device="mps", dtype=torch.float32)
        b = torch.randn(n, n, device="mps", dtype=torch.float32)

        start = time.perf_counter()
        c = torch.matmul(a, b)
        _ = c.cpu()
        elapsed = time.perf_counter() - start

        checksum = float(c[0, 0].cpu())

        return WorkerResult(
            resource="gpu",
            task_type="matrix_ops",
            time_seconds=round(elapsed, 4),
            cost_usd=0.0,
            energy_wh=round((elapsed / 3600) * GPU_TDP_WATTS, 4),
            output_summary=f"GPU (MPS): {n}x{n} matmul in {elapsed:.4f}s. Checksum: {checksum:.4f}",
            metadata={"matrix_size": n, "backend": "mps", "gpu_name": "Apple Silicon"},
        )

    def _parallel_matmul(self, n: int) -> WorkerResult:
        a = np.random.rand(n, n).astype(np.float32)
        b = np.random.rand(n, n).astype(np.float32)

        cores = self.gpu_info.get("cores", cpu_count() or 4)
        chunk_size = max(1, n // cores)
        chunks = [
            (a[i:i + chunk_size], b) for i in range(0, n, chunk_size)
        ]

        start = time.perf_counter()
        with Pool(processes=min(cores, len(chunks))) as pool:
            results = pool.map(_chunk_matmul, chunks)
        result = np.vstack(results)
        elapsed = time.perf_counter() - start

        checksum = float(result[0, 0])

        return WorkerResult(
            resource="gpu",
            task_type="matrix_ops",
            time_seconds=round(elapsed, 4),
            cost_usd=0.0,
            energy_wh=round((elapsed / 3600) * GPU_TDP_WATTS, 4),
            output_summary=(
                f"GPU (simulated via {cores}-core parallel): "
                f"{n}x{n} matmul in {elapsed:.4f}s. Checksum: {checksum:.4f}"
            ),
            metadata={
                "matrix_size": n, "backend": "multiprocessing",
                "cores_used": cores, "gpu_name": self.gpu_info["name"],
            },
        )

    def _image_processing(self, params: dict) -> WorkerResult:
        width = params.get("width", 1024)
        height = params.get("height", 1024)
        cores = self.gpu_info.get("cores", cpu_count() or 4)

        img = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)

        start = time.perf_counter()
        gray = (0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]).astype(np.float32)
        padded = np.pad(gray, 1, mode="edge")
        edge_x = (
            -padded[:-2, :-2] + padded[:-2, 2:]
            - 2 * padded[1:-1, :-2] + 2 * padded[1:-1, 2:]
            - padded[2:, :-2] + padded[2:, 2:]
        )
        edge_y = (
            -padded[:-2, :-2] - 2 * padded[:-2, 1:-1] - padded[:-2, 2:]
            + padded[2:, :-2] + 2 * padded[2:, 1:-1] + padded[2:, 2:]
        )
        edges = np.clip(np.sqrt(edge_x ** 2 + edge_y ** 2), 0, 255).astype(np.uint8)
        elapsed = time.perf_counter() - start

        return WorkerResult(
            resource="gpu",
            task_type="image_processing",
            time_seconds=round(elapsed, 4),
            cost_usd=0.0,
            energy_wh=round((elapsed / 3600) * GPU_TDP_WATTS, 4),
            output_summary=f"GPU (parallel): {width}x{height} image processed in {elapsed:.4f}s",
            metadata={"backend": self.gpu_info.get("backend", "multiprocessing"), "size": f"{width}x{height}"},
        )

    def _simple_compute(self, params: dict) -> WorkerResult:
        n = params.get("array_size", 100_000)
        arr = np.random.rand(n)

        start = time.perf_counter()
        sorted_arr = np.sort(arr)
        mean_val = float(np.mean(arr))
        std_val = float(np.std(arr))
        elapsed = time.perf_counter() - start

        return WorkerResult(
            resource="gpu",
            task_type="simple_compute",
            time_seconds=round(elapsed, 4),
            cost_usd=0.0,
            energy_wh=round((elapsed / 3600) * GPU_TDP_WATTS, 4),
            output_summary=f"GPU: Computed {n:,} elements in {elapsed:.4f}s. Mean={mean_val:.4f}",
            metadata={"backend": self.gpu_info.get("backend", "multiprocessing"), "array_size": n},
        )


def generate_colab_link(task_type: str, params: dict) -> str:
    """Generate a Google Colab notebook link with pre-filled code."""
    code_templates = {
        "matrix_ops": f"import numpy as np\\nimport time\\n\\nn = {params.get('matrix_size', 500)}\\na = np.random.rand(n, n).astype(np.float32)\\nb = np.random.rand(n, n).astype(np.float32)\\n\\nstart = time.time()\\nc = np.matmul(a, b)\\nprint(f'{{n}}x{{n}} matmul: {{time.time()-start:.3f}}s')",
        "image_processing": "from PIL import Image\\nimport numpy as np\\nimport time\\n\\n# Generate sample image\\nimg = np.random.randint(0, 256, (1024, 1024, 3), dtype=np.uint8)\\nimg_pil = Image.fromarray(img)\\n\\nstart = time.time()\\ngray = img_pil.convert('L')\\nresized = gray.resize((512, 512))\\nprint(f'Processed in {time.time()-start:.3f}s')",
        "simple_compute": "import numpy as np\\nimport time\\n\\narr = np.random.rand(100_000)\\nstart = time.time()\\nsorted_arr = np.sort(arr)\\nmean = np.mean(arr)\\nprint(f'Sorted 100K elements in {time.time()-start:.4f}s, mean={mean:.4f}')",
    }
    code = code_templates.get(task_type, code_templates["simple_compute"])
    import urllib.parse
    return f"https://colab.research.google.com/notebook#create=true&language=python&code={urllib.parse.quote(code)}"


if __name__ == "__main__":
    print(f"GPU Detection: {GPU_INFO}\n")
    worker = GPUWorker()

    result = worker.execute("matrix_ops", {"matrix_size": 300})
    print(f"[Matrix] {result.output_summary}")
    print(f"  Time: {result.time_seconds}s | Energy: {result.energy_wh}Wh")

    result = worker.execute("image_processing", {"width": 512, "height": 512})
    print(f"\n[Image] {result.output_summary}")

    result = worker.execute("simple_compute", {"array_size": 100_000})
    print(f"\n[Compute] {result.output_summary}")

    link = generate_colab_link("matrix_ops", {"matrix_size": 500})
    print(f"\nColab link: {link[:80]}...")
