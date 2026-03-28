import time
import random
import numpy as np
from base_worker import BaseWorker, WorkerResult

CLOUD_RATE_PER_HOUR = 0.50
CLOUD_TDP_WATTS = 15


class CloudWorker(BaseWorker):
    """Simulated cloud execution with realistic network latency and cost tracking."""

    resource_name = "cloud"

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

    def _simulate_network(self, data_size_mb: float = 1.0) -> float:
        """Simulate realistic network latency: handshake + transfer + jitter."""
        handshake = random.uniform(0.5, 2.0)
        transfer = data_size_mb * random.uniform(0.1, 0.5)
        jitter = random.uniform(0, 0.3)
        total = handshake + transfer + jitter
        time.sleep(min(total, 3.0))
        return total

    def _matrix_multiply(self, params: dict) -> WorkerResult:
        n = params.get("matrix_size", 500)
        data_mb = (n * n * 4 * 2) / (1024 * 1024)

        network_time = self._simulate_network(data_mb)

        a = np.random.rand(n, n).astype(np.float32)
        b = np.random.rand(n, n).astype(np.float32)
        start = time.perf_counter()
        result = np.matmul(a, b)
        compute_time = time.perf_counter() - start

        total_time = network_time + compute_time
        cost = max(0.01, (total_time / 3600) * CLOUD_RATE_PER_HOUR)
        checksum = float(result[0, 0])

        return WorkerResult(
            resource="cloud",
            task_type="matrix_ops",
            time_seconds=round(total_time, 4),
            cost_usd=round(cost, 4),
            energy_wh=round((total_time / 3600) * CLOUD_TDP_WATTS, 4),
            output_summary=(
                f"Cloud: {n}x{n} matmul in {total_time:.3f}s "
                f"(network: {network_time:.2f}s + compute: {compute_time:.4f}s). "
                f"Cost: ${cost:.4f}"
            ),
            metadata={
                "matrix_size": n,
                "network_time": round(network_time, 3),
                "compute_time": round(compute_time, 4),
                "region": "ap-south-1 (Mumbai)",
                "instance_type": "t3.medium (simulated)",
                "checksum": checksum,
            },
        )

    def _image_processing(self, params: dict) -> WorkerResult:
        width = params.get("width", 1024)
        height = params.get("height", 1024)
        data_mb = (width * height * 3) / (1024 * 1024)

        network_time = self._simulate_network(data_mb)

        img = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        start = time.perf_counter()
        gray = (0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]).astype(np.float32)
        padded = np.pad(gray, 1, mode="edge")
        edge_x = -padded[:-2, :-2] + padded[:-2, 2:] - 2 * padded[1:-1, :-2] + 2 * padded[1:-1, 2:] - padded[2:, :-2] + padded[2:, 2:]
        edge_y = -padded[:-2, :-2] - 2 * padded[:-2, 1:-1] - padded[:-2, 2:] + padded[2:, :-2] + 2 * padded[2:, 1:-1] + padded[2:, 2:]
        edges = np.clip(np.sqrt(edge_x ** 2 + edge_y ** 2), 0, 255).astype(np.uint8)
        compute_time = time.perf_counter() - start

        total_time = network_time + compute_time
        cost = max(0.01, (total_time / 3600) * CLOUD_RATE_PER_HOUR)

        return WorkerResult(
            resource="cloud",
            task_type="image_processing",
            time_seconds=round(total_time, 4),
            cost_usd=round(cost, 4),
            energy_wh=round((total_time / 3600) * CLOUD_TDP_WATTS, 4),
            output_summary=(
                f"Cloud: {width}x{height} image processed in {total_time:.3f}s. Cost: ${cost:.4f}"
            ),
            metadata={
                "network_time": round(network_time, 3),
                "compute_time": round(compute_time, 4),
                "region": "ap-south-1 (Mumbai)",
            },
        )

    def _simple_compute(self, params: dict) -> WorkerResult:
        n = params.get("array_size", 100_000)

        network_time = self._simulate_network(0.5)

        arr = np.random.rand(n)
        start = time.perf_counter()
        np.sort(arr)
        mean_val = float(np.mean(arr))
        compute_time = time.perf_counter() - start

        total_time = network_time + compute_time
        cost = max(0.01, (total_time / 3600) * CLOUD_RATE_PER_HOUR)

        return WorkerResult(
            resource="cloud",
            task_type="simple_compute",
            time_seconds=round(total_time, 4),
            cost_usd=round(cost, 4),
            energy_wh=round((total_time / 3600) * CLOUD_TDP_WATTS, 4),
            output_summary=(
                f"Cloud: {n:,} elements computed in {total_time:.3f}s. "
                f"Cost: ${cost:.4f}. Mean={mean_val:.4f}"
            ),
            metadata={
                "network_time": round(network_time, 3),
                "compute_time": round(compute_time, 4),
                "region": "ap-south-1 (Mumbai)",
            },
        )


if __name__ == "__main__":
    worker = CloudWorker()

    result = worker.execute("matrix_ops", {"matrix_size": 300})
    print(f"[Matrix] {result.output_summary}")
    print(f"  Cost: ${result.cost_usd} | Energy: {result.energy_wh}Wh")

    result = worker.execute("simple_compute", {"array_size": 100_000})
    print(f"\n[Compute] {result.output_summary}")
