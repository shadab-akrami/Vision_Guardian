"""
Storage Manager for VisionGuardian
Manages storage efficiently within 32GB SD card constraints
Optimized for Raspberry Pi 5
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import psutil
import glob

from utils import Config, LOGS_DIR, CACHE_DIR, MODELS_DIR, DATA_DIR


class StorageManager:
    """Manages storage and performs automatic cleanup"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger('VisionGuardian.StorageManager')

        # Storage thresholds
        self.warning_threshold_gb = config.get('system.storage_warning_threshold_gb', 5)
        self.critical_threshold_gb = 2  # Critical warning at 2GB

        # Cleanup settings
        self.auto_cleanup = config.get('storage.auto_cleanup', True)
        self.keep_logs_days = config.get('storage.keep_logs_days', 7)
        self.keep_cache_hours = config.get('storage.keep_cache_hours', 24)

    def get_storage_info(self) -> Dict[str, float]:
        """
        Get current storage information

        Returns:
            Dictionary with storage stats
        """
        disk = psutil.disk_usage('/')
        return {
            'total_gb': disk.total / (1024**3),
            'used_gb': disk.used / (1024**3),
            'free_gb': disk.free / (1024**3),
            'percent_used': disk.percent
        }

    def check_storage_health(self) -> Tuple[str, str]:
        """
        Check storage health status

        Returns:
            Tuple of (status, message)
            status: 'ok', 'warning', 'critical'
        """
        info = self.get_storage_info()
        free_gb = info['free_gb']

        if free_gb < self.critical_threshold_gb:
            return ('critical', f"Critical: Only {free_gb:.2f} GB free!")
        elif free_gb < self.warning_threshold_gb:
            return ('warning', f"Warning: {free_gb:.2f} GB free")
        else:
            return ('ok', f"Storage OK: {free_gb:.2f} GB free")

    def get_directory_size(self, directory: Path) -> float:
        """
        Calculate directory size in MB

        Args:
            directory: Path to directory

        Returns:
            Size in MB
        """
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            self.logger.error(f"Error calculating directory size for {directory}: {e}")

        return total_size / (1024**2)  # Convert to MB

    def get_storage_breakdown(self) -> Dict[str, float]:
        """
        Get storage breakdown by directory

        Returns:
            Dictionary with directory sizes in MB
        """
        breakdown = {
            'logs': self.get_directory_size(LOGS_DIR),
            'cache': self.get_directory_size(CACHE_DIR),
            'models': self.get_directory_size(MODELS_DIR),
            'data': self.get_directory_size(DATA_DIR),
        }

        breakdown['total'] = sum(breakdown.values())
        return breakdown

    def clean_old_logs(self, days: int = None) -> int:
        """
        Remove log files older than specified days

        Args:
            days: Number of days to keep (default from config)

        Returns:
            Number of files deleted
        """
        if days is None:
            days = self.keep_logs_days

        deleted_count = 0
        cutoff_time = datetime.now() - timedelta(days=days)

        try:
            for log_file in LOGS_DIR.glob('*.log*'):
                if log_file.is_file():
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        log_file.unlink()
                        deleted_count += 1
                        self.logger.info(f"Deleted old log: {log_file.name}")
        except Exception as e:
            self.logger.error(f"Error cleaning logs: {e}")

        return deleted_count

    def clean_cache(self, hours: int = None) -> int:
        """
        Remove cache files older than specified hours

        Args:
            hours: Number of hours to keep (default from config)

        Returns:
            Number of files deleted
        """
        if hours is None:
            hours = self.keep_cache_hours

        deleted_count = 0
        cutoff_time = datetime.now() - timedelta(hours=hours)

        try:
            for cache_file in CACHE_DIR.glob('*'):
                if cache_file.is_file():
                    file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        cache_file.unlink()
                        deleted_count += 1
                        self.logger.debug(f"Deleted cache file: {cache_file.name}")
        except Exception as e:
            self.logger.error(f"Error cleaning cache: {e}")

        return deleted_count

    def rotate_log_file(self, log_path: Path, max_size_mb: float = 100) -> bool:
        """
        Rotate log file if it exceeds max size

        Args:
            log_path: Path to log file
            max_size_mb: Maximum size before rotation

        Returns:
            True if rotated, False otherwise
        """
        try:
            if log_path.exists():
                size_mb = log_path.stat().st_size / (1024**2)
                if size_mb > max_size_mb:
                    # Create rotated filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    rotated_path = log_path.with_name(f"{log_path.stem}_{timestamp}.log")

                    # Rename current log
                    shutil.move(str(log_path), str(rotated_path))
                    self.logger.info(f"Rotated log file: {log_path.name} -> {rotated_path.name}")
                    return True
        except Exception as e:
            self.logger.error(f"Error rotating log file {log_path}: {e}")

        return False

    def cleanup_unknown_faces(self, max_keep: int = 100) -> int:
        """
        Remove old unknown face images, keeping only recent ones

        Args:
            max_keep: Maximum number of unknown faces to keep

        Returns:
            Number of files deleted
        """
        unknown_faces_dir = DATA_DIR / 'unknown_faces'
        if not unknown_faces_dir.exists():
            return 0

        deleted_count = 0
        try:
            # Get all unknown face images sorted by modification time
            face_files = sorted(
                unknown_faces_dir.glob('*.jpg'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # Delete old files beyond max_keep
            for face_file in face_files[max_keep:]:
                face_file.unlink()
                deleted_count += 1
                self.logger.debug(f"Deleted old unknown face: {face_file.name}")

        except Exception as e:
            self.logger.error(f"Error cleaning unknown faces: {e}")

        return deleted_count

    def perform_cleanup(self) -> Dict[str, int]:
        """
        Perform full cleanup operation

        Returns:
            Dictionary with cleanup statistics
        """
        self.logger.info("Starting automatic cleanup...")

        stats = {
            'logs_deleted': 0,
            'cache_deleted': 0,
            'unknown_faces_deleted': 0
        }

        if self.auto_cleanup:
            stats['logs_deleted'] = self.clean_old_logs()
            stats['cache_deleted'] = self.clean_cache()
            stats['unknown_faces_deleted'] = self.cleanup_unknown_faces()

            total = sum(stats.values())
            self.logger.info(f"Cleanup complete: {total} files deleted")
        else:
            self.logger.info("Auto cleanup disabled")

        return stats

    def emergency_cleanup(self) -> bool:
        """
        Perform emergency cleanup when storage is critically low

        Returns:
            True if successful, False otherwise
        """
        self.logger.warning("Performing emergency cleanup!")

        try:
            # More aggressive cleanup
            self.clean_old_logs(days=3)  # Keep only 3 days of logs
            self.clean_cache(hours=6)    # Keep only 6 hours of cache
            self.cleanup_unknown_faces(max_keep=20)  # Keep only 20 unknown faces

            # Clear all cache
            for cache_file in CACHE_DIR.glob('*'):
                if cache_file.is_file():
                    cache_file.unlink()

            self.logger.info("Emergency cleanup completed")
            return True

        except Exception as e:
            self.logger.error(f"Emergency cleanup failed: {e}")
            return False

    def optimize_storage(self) -> Dict[str, any]:
        """
        Optimize storage by compressing and organizing files

        Returns:
            Dictionary with optimization results
        """
        results = {
            'compressed_files': 0,
            'space_saved_mb': 0,
            'errors': []
        }

        # Future: Implement model compression, log compression, etc.
        self.logger.info("Storage optimization not yet implemented")

        return results

    def get_storage_report(self) -> str:
        """
        Generate comprehensive storage report

        Returns:
            Formatted storage report string
        """
        info = self.get_storage_info()
        breakdown = self.get_storage_breakdown()
        status, message = self.check_storage_health()

        report = []
        report.append("=" * 60)
        report.append("STORAGE REPORT")
        report.append("=" * 60)
        report.append(f"\nOverall Status: {status.upper()} - {message}")
        report.append(f"\nTotal Storage: {info['total_gb']:.2f} GB")
        report.append(f"Used: {info['used_gb']:.2f} GB ({info['percent_used']:.1f}%)")
        report.append(f"Free: {info['free_gb']:.2f} GB")
        report.append(f"\nProject Storage Breakdown:")
        report.append(f"  Logs:   {breakdown['logs']:.2f} MB")
        report.append(f"  Cache:  {breakdown['cache']:.2f} MB")
        report.append(f"  Models: {breakdown['models']:.2f} MB")
        report.append(f"  Data:   {breakdown['data']:.2f} MB")
        report.append(f"  Total:  {breakdown['total']:.2f} MB")
        report.append("=" * 60)

        return "\n".join(report)

    def monitor_storage(self) -> Tuple[str, bool]:
        """
        Monitor storage and trigger cleanup if needed

        Returns:
            Tuple of (status_message, needs_attention)
        """
        status, message = self.check_storage_health()

        if status == 'critical':
            self.logger.critical(message)
            self.emergency_cleanup()
            return (message, True)
        elif status == 'warning':
            self.logger.warning(message)
            self.perform_cleanup()
            return (message, True)
        else:
            self.logger.debug(message)
            return (message, False)


def test_storage_manager():
    """Test storage manager functionality"""
    from utils import setup_logging

    setup_logging("INFO", "storage_test.log")
    config = Config()
    manager = StorageManager(config)

    print(manager.get_storage_report())

    print("\nTesting cleanup...")
    stats = manager.perform_cleanup()
    print(f"Cleanup stats: {stats}")


if __name__ == "__main__":
    test_storage_manager()
