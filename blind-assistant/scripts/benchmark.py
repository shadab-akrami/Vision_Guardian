#!/usr/bin/env python3
"""
Benchmarking tool for VisionGuardian
Tests performance of all modules on Raspberry Pi 5
"""

import sys
import time
import cv2
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils import Config, setup_logging, get_system_info
from camera_handler import CameraHandler
from facial_recognition import FacialRecognition
from object_detection import ObjectDetection
from ocr_module import OCRModule
from obstacle_detection import ObstacleDetection


def benchmark_camera(camera, iterations=100):
    """Benchmark camera capture"""
    print("\nBenchmarking Camera Capture...")

    start_time = time.time()
    frame_count = 0

    for _ in range(iterations):
        frame = camera.get_current_frame()
        if frame is not None:
            frame_count += 1

    duration = time.time() - start_time
    fps = frame_count / duration

    print(f"  Frames captured: {frame_count}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Average FPS: {fps:.2f}")
    print(f"  Frame time: {1000/fps:.2f}ms")

    return {'fps': fps, 'frame_time_ms': 1000/fps}


def benchmark_facial_recognition(face_rec, test_frame, iterations=10):
    """Benchmark facial recognition"""
    print("\nBenchmarking Facial Recognition...")

    times = []

    for _ in range(iterations):
        start = time.time()
        faces = face_rec.recognize_faces(test_frame)
        elapsed = time.time() - start
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    fps = 1.0 / avg_time

    print(f"  Iterations: {iterations}")
    print(f"  Average time: {avg_time*1000:.2f}ms")
    print(f"  Throughput: {fps:.2f} FPS")
    print(f"  Min time: {min(times)*1000:.2f}ms")
    print(f"  Max time: {max(times)*1000:.2f}ms")

    return {'avg_time_ms': avg_time*1000, 'fps': fps}


def benchmark_object_detection(obj_det, test_frame, iterations=20):
    """Benchmark object detection"""
    print("\nBenchmarking Object Detection...")

    times = []

    for _ in range(iterations):
        start = time.time()
        objects = obj_det.detect_objects(test_frame, force=True)
        elapsed = time.time() - start
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    fps = 1.0 / avg_time

    print(f"  Iterations: {iterations}")
    print(f"  Average time: {avg_time*1000:.2f}ms")
    print(f"  Throughput: {fps:.2f} FPS")
    print(f"  Min time: {min(times)*1000:.2f}ms")
    print(f"  Max time: {max(times)*1000:.2f}ms")

    return {'avg_time_ms': avg_time*1000, 'fps': fps}


def benchmark_ocr(ocr, test_frame, iterations=10):
    """Benchmark OCR"""
    print("\nBenchmarking OCR...")

    times = []

    for _ in range(iterations):
        start = time.time()
        result = ocr.read_text(test_frame)
        elapsed = time.time() - start
        times.append(elapsed)

    avg_time = sum(times) / len(times)

    print(f"  Iterations: {iterations}")
    print(f"  Average time: {avg_time*1000:.2f}ms")
    print(f"  Min time: {min(times)*1000:.2f}ms")
    print(f"  Max time: {max(times)*1000:.2f}ms")

    return {'avg_time_ms': avg_time*1000}


def benchmark_obstacle_detection(obs_det, test_frame, iterations=20):
    """Benchmark obstacle detection"""
    print("\nBenchmarking Obstacle Detection...")

    times = []

    for _ in range(iterations):
        start = time.time()
        obstacles = obs_det.detect_obstacles(test_frame)
        elapsed = time.time() - start
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    fps = 1.0 / avg_time

    print(f"  Iterations: {iterations}")
    print(f"  Average time: {avg_time*1000:.2f}ms")
    print(f"  Throughput: {fps:.2f} FPS")

    return {'avg_time_ms': avg_time*1000, 'fps': fps}


def main():
    print("=" * 70)
    print("VisionGuardian Performance Benchmark")
    print("Optimized for Raspberry Pi 5 (64-bit ARM64)")
    print("=" * 70)

    # Setup
    setup_logging("ERROR")  # Reduce log noise during benchmark
    config = Config()

    # Print system info
    print("\nSystem Information:")
    print("-" * 70)
    info = get_system_info()
    for key, value in info.items():
        print(f"  {key:25s}: {value}")

    results = {}

    # Initialize camera
    print("\n" + "=" * 70)
    print("Initializing Components...")
    print("=" * 70)

    camera = CameraHandler(config)
    if not camera.initialize():
        print("Failed to initialize camera")
        return 1

    camera.start_capture()
    time.sleep(2)  # Let camera warm up

    # Get test frame
    test_frame = camera.get_current_frame()
    if test_frame is None:
        print("Failed to capture test frame")
        return 1

    print(f"Test frame size: {test_frame.shape[1]}x{test_frame.shape[0]}")

    # Run benchmarks
    print("\n" + "=" * 70)
    print("Running Benchmarks...")
    print("=" * 70)

    # Camera benchmark
    results['camera'] = benchmark_camera(camera)

    # Facial recognition
    face_rec = FacialRecognition(config)
    if face_rec.initialize():
        results['facial_recognition'] = benchmark_facial_recognition(face_rec, test_frame)
    else:
        print("\nFacial recognition not available")

    # Object detection
    obj_det = ObjectDetection(config)
    if obj_det.initialize():
        results['object_detection'] = benchmark_object_detection(obj_det, test_frame)
    else:
        print("\nObject detection not available (download model first)")

    # OCR
    ocr = OCRModule(config)
    if ocr.initialize():
        results['ocr'] = benchmark_ocr(ocr, test_frame)
    else:
        print("\nOCR not available")

    # Obstacle detection
    obs_det = ObstacleDetection(config)
    if obs_det.initialize():
        results['obstacle_detection'] = benchmark_obstacle_detection(obs_det, test_frame)

    # Cleanup
    camera.release()

    # Print summary
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)

    for module, stats in results.items():
        print(f"\n{module.upper()}:")
        for key, value in stats.items():
            print(f"  {key:20s}: {value:.2f}")

    # Performance assessment
    print("\n" + "=" * 70)
    print("PERFORMANCE ASSESSMENT")
    print("=" * 70)

    if 'camera' in results:
        fps = results['camera']['fps']
        if fps >= 15:
            status = "EXCELLENT"
        elif fps >= 10:
            status = "GOOD"
        else:
            status = "NEEDS IMPROVEMENT"
        print(f"\nCamera FPS: {fps:.1f} - {status}")

    if 'object_detection' in results:
        fps = results['object_detection']['fps']
        if fps >= 10:
            status = "EXCELLENT"
        elif fps >= 5:
            status = "GOOD"
        else:
            status = "ACCEPTABLE"
        print(f"Object Detection: {fps:.1f} FPS - {status}")

    if 'facial_recognition' in results:
        time_ms = results['facial_recognition']['avg_time_ms']
        if time_ms < 1000:
            status = "EXCELLENT"
        elif time_ms < 2000:
            status = "GOOD"
        else:
            status = "ACCEPTABLE"
        print(f"Facial Recognition: {time_ms:.0f}ms - {status}")

    if 'ocr' in results:
        time_ms = results['ocr']['avg_time_ms']
        if time_ms < 2000:
            status = "EXCELLENT"
        elif time_ms < 4000:
            status = "GOOD"
        else:
            status = "ACCEPTABLE"
        print(f"OCR: {time_ms:.0f}ms - {status}")

    print("\n" + "=" * 70)
    print("Benchmark completed!")
    print("=" * 70)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
