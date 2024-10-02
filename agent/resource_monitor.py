import psutil
import time

class ResourceMonitor:
    def monitor(self, interval=0.1):
        # Step 1: Get the total CPU usage over the interval
        cpu_usage_total = psutil.cpu_percent(interval=interval)

        # Step 2: Get memory usage
        memory_info = psutil.virtual_memory()
        memory_usage = memory_info.percent

        # Start measurements for disk and network I/O
        disk_io_start = psutil.disk_io_counters(perdisk=False)
        net_io_start = psutil.net_io_counters()

        # Wait for the interval duration to calculate changes in disk and network usage
        time.sleep(interval)

        # End measurements for disk and network I/O
        disk_io_end = psutil.disk_io_counters(perdisk=False)
        net_io_end = psutil.net_io_counters()

        # Calculate disk read/write speeds in MB/s
        read_bytes = disk_io_end.read_bytes - disk_io_start.read_bytes
        write_bytes = disk_io_end.write_bytes - disk_io_start.write_bytes
        read_speed = (read_bytes / (1024 ** 2)) / interval  # MB/s
        write_speed = (write_bytes / (1024 ** 2)) / interval  # MB/s

        # Calculate network send/receive speeds in MB/s
        net_send_bytes = net_io_end.bytes_sent - net_io_start.bytes_sent
        net_recv_bytes = net_io_end.bytes_recv - net_io_start.bytes_recv
        net_send_speed = (net_send_bytes / (1024 ** 2)) / interval  # MB/s
        net_recv_speed = (net_recv_bytes / (1024 ** 2)) / interval  # MB/s

        return {
            'cpu_total': cpu_usage_total,
            'memory': memory_usage,
            'disk_read_MBps': read_speed,
            'disk_write_MBps': write_speed,
            'net_send_MBps': net_send_speed,
            'net_recv_MBps': net_recv_speed
        }

# Create an instance of ResourceMonitor

