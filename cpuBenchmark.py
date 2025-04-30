import time

def cpu_benchmark():
    start = time.time()
    pi = 0
    for i in range(1, 1000000, 2):
        pi += 4 / i - 4 / (i + 2)
    end = time.time()
    elapsed = end - start
    return elapsed

if __name__ == "__main__":
    time_taken = cpu_benchmark()
    print(f"Benchmark complete. Time taken: {time_taken:.4f} seconds")
