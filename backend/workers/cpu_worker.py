import time
import numpy as np
from typing import Dict, Any
from base_worker import BaseWorker, WorkerResult

CPU_TDP_WATTS = 65


class CPUWorker(BaseWorker):
    resource_name = "cpu"

    def is_available(self) -> bool:
        return True

    def execute(self, task_type: str, params: dict) -> WorkerResult:
        dispatch = {
            "matrix_ops": self._matrix_multiply,
            "image_processing": self._image_processing,
            "simple_compute": self._simple_compute,
            "data_processing": self._data_processing,
            "ml_training": self._simple_compute,
            "nlp": self._simple_compute,
            "simulation": self._simple_compute,
        }
        handler = dispatch.get(task_type, self._simple_compute)
        return handler(params)

    # ── Matrix multiplication ────────────────────────────────────────

    def _matrix_multiply(self, params: dict) -> WorkerResult:
        n = params.get("matrix_size", 500)
        a = np.random.rand(n, n).astype(np.float32)
        b = np.random.rand(n, n).astype(np.float32)

        start = time.perf_counter()
        result = np.matmul(a, b)
        elapsed = time.perf_counter() - start

        checksum = float(result[0, 0])

        return WorkerResult(
            resource="cpu",
            task_type="matrix_ops",
            time_seconds=round(elapsed, 4),
            cost_usd=0.0,
            energy_wh=round((elapsed / 3600) * CPU_TDP_WATTS, 4),
            output_summary=f"Multiplied {n}x{n} matrices in {elapsed:.3f}s. Checksum: {checksum:.4f}",
            metadata={
                "matrix_size": n,
                "dtype": "float32",
                "checksum": checksum,
                "flops_approx": 2 * n ** 3,
            },
        )

    # ── Image processing ─────────────────────────────────────────────

    def _image_processing(self, params: dict) -> WorkerResult:
        width = params.get("width", 1024)
        height = params.get("height", 1024)

        img = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)

        start = time.perf_counter()

        gray = (0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]).astype(np.float32)

        # Sobel edge detection (fully vectorized, no Python loops)
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

        new_h, new_w = height // 2, width // 2
        resized = gray[::2, ::2][:new_h, :new_w]

        elapsed = time.perf_counter() - start

        return WorkerResult(
            resource="cpu",
            task_type="image_processing",
            time_seconds=round(elapsed, 4),
            cost_usd=0.0,
            energy_wh=round((elapsed / 3600) * CPU_TDP_WATTS, 4),
            output_summary=(
                f"Processed {width}x{height} image: grayscale + edge detection + "
                f"resize to {new_w}x{new_h} in {elapsed:.3f}s"
            ),
            metadata={
                "original_size": f"{width}x{height}",
                "operations": ["grayscale", "sobel_edge_detection", "resize_half"],
                "edge_mean": float(np.mean(edges)),
            },
        )

    # ── Simple compute ───────────────────────────────────────────────

    def _simple_compute(self, params: dict) -> WorkerResult:
        n = params.get("array_size", 100_000)
        arr = np.random.rand(n)

        start = time.perf_counter()
        sorted_arr = np.sort(arr)
        mean_val = float(np.mean(arr))
        std_val = float(np.std(arr))
        median_val = float(np.median(arr))
        p95 = float(np.percentile(arr, 95))
        elapsed = time.perf_counter() - start

        return WorkerResult(
            resource="cpu",
            task_type="simple_compute",
            time_seconds=round(elapsed, 4),
            cost_usd=0.0,
            energy_wh=round((elapsed / 3600) * CPU_TDP_WATTS, 4),
            output_summary=(
                f"Sorted {n:,} elements + computed statistics in {elapsed:.4f}s. "
                f"Mean={mean_val:.4f}, Std={std_val:.4f}"
            ),
            metadata={
                "array_size": n,
                "mean": mean_val,
                "std": std_val,
                "median": median_val,
                "p95": p95,
            },
        )

    # ── Data processing ──────────────────────────────────────────────

    def _data_processing(self, params: dict) -> WorkerResult:
        n = params.get("num_rows", 50_000)
        data = {
            "id": np.arange(n),
            "value": np.random.rand(n) * 1000,
            "category": np.random.choice(["A", "B", "C", "D"], n),
        }

        start = time.perf_counter()
        sorted_idx = np.argsort(data["value"])
        sorted_values = data["value"][sorted_idx]

        cat_means: Dict[str, Any] = {}
        for cat in ["A", "B", "C", "D"]:
            mask = data["category"] == cat
            cat_means[cat] = float(np.mean(data["value"][mask]))

        top_10 = sorted_values[-10:][::-1]
        elapsed = time.perf_counter() - start

        return WorkerResult(
            resource="cpu",
            task_type="data_processing",
            time_seconds=round(elapsed, 4),
            cost_usd=0.0,
            energy_wh=round((elapsed / 3600) * CPU_TDP_WATTS, 4),
            output_summary=(
                f"Processed {n:,} rows: sort + group-by aggregation in {elapsed:.4f}s"
            ),
            metadata={
                "num_rows": n,
                "category_means": cat_means,
                "top_value": float(top_10[0]),
            },
        )


if __name__ == "__main__":
    worker = CPUWorker()
    print(f"CPU Worker available: {worker.is_available()}\n")

    tests = [
        ("matrix_ops", {"matrix_size": 200}),
        ("image_processing", {"width": 512, "height": 512}),
        ("simple_compute", {"array_size": 100_000}),
        ("data_processing", {"num_rows": 50_000}),
    ]

    for task_type, params in tests:
        result = worker.execute(task_type, params)
        print(f"[{result.task_type}] {result.output_summary}")
        print(f"  Time: {result.time_seconds}s | Cost: ${result.cost_usd} | Energy: {result.energy_wh}Wh\n")
