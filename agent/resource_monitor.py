import psutil
import time

class ResourceMonitor:
    def monitor(self, interval=0.1):
        timings = {}

        # Step 1: Measure CPU usage calculation time
        start_time = time.time()
        cpu_usage_total = psutil.cpu_percent(0)
        timings['cpu_usage_time'] = time.time() - start_time

        # Step 2: Measure memory usage calculation time
        start_time = time.time()
        memory_info = psutil.virtual_memory()
        memory_usage = memory_info.percent
        timings['memory_usage_time'] = time.time() - start_time

        # Step 3: Measure start disk and network I/O collection time
        start_time = time.time()
        disk_io_start = psutil.disk_io_counters(perdisk=False)
        net_io_start = psutil.net_io_counters()
        timings['io_start_time'] = time.time() - start_time

      

        # Step 4: Measure end disk and network I/O collection time
        start_time = time.time()
        disk_io_end = psutil.disk_io_counters(perdisk=False)
        net_io_end = psutil.net_io_counters()
        timings['io_end_time'] = time.time() - start_time

        # Step 5: Measure calculation time for speeds
        start_time = time.time()
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
        timings['calculation_time'] = time.time() - start_time

        # Return results with timings
        return {
            'cpu_total': cpu_usage_total,
            'memory': memory_usage,
            'disk_read_MBps': read_speed,
            'disk_write_MBps': write_speed,
            'net_send_MBps': net_send_speed,
            'net_recv_MBps': net_recv_speed,
            'timings': timings
        }


