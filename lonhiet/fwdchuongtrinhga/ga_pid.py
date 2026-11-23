import serial
import os
import time
import random
import numpy as np
import matlab.engine

# ================= CAU HINH GIAI THUAT DI TRUYEN (GA) =================
POP_SIZE = 20          # So ca the moi the he
GENERATIONS = 25       # So the he tien hoa (20 x 25 = 500 luot -> chay ~20-35 giay)
CROSSOVER_RATE = 0.85  # Xac suat lai ghep
MUTATION_RATE = 0.20   # Xac suat dot bien
ELITISM_COUNT = 2      # Giu lai 2 ca the tot nhat moi the he

# Dai tim kiem [min, max] cho Kp, Ki, Kd (bam sat bai toan lo nhiet)
BOUNDS = [
    (0.1, 160.0),   # Kp
    (0.0, 160.0),   # Ki
    (0.0, 160.0),   # Kd
]

# ================= HAM PHAT MEM (CHUAN Y TU - KHONG LAM GA BI "SO") =================
def evaluate_individual(eng, chrom):
    kp, ki, kd = float(chrom[0]), float(chrom[1]), float(chrom[2])
    try:
        t_xl, pot, e_xl, stable, max_re = eng.eval_pid_lonhiet(kp, ki, kd, nargout=5)
        t_xl = float(t_xl)
        pot = float(pot)
        e_xl = float(e_xl)
        stable = int(stable)
        max_re = float(max_re)
    except Exception:
        return 1e5, (100.0, 100.0, 150.0, 0)

    if stable == 0:
        # Phat mem co do doc theo max_re: cang sat vung on dinh thi phat cang nhe
        # Giup GA biet giu cac ca the "suyt on dinh" de lai ghep keo ve vung on dinh
        cost = 500.0 + 200.0 * max(0.0, max_re)
    else:
        # Ep thoi gian xac lap (t_xl), do vot lo (pot) va sai so xac lap (e_xl) ve thap nhat
        cost = 5.0 * t_xl + 2.0 * pot + 10.0 * e_xl

        # Phat mem them neu vot lo vuot 2% hoac xac lap qua cham (> 10s)
        if pot > 2.0:
            cost += 3.0 * (pot - 2.0)
        if t_xl > 10.0:
            cost += 2.0 * (t_xl - 10.0)

    return cost, (t_xl, pot, e_xl, stable)


def init_population():
    pop = []
    for _ in range(POP_SIZE):
        chrom = [random.uniform(low, high) for (low, high) in BOUNDS]
        pop.append(chrom)
    return pop


def tournament_select(pop, costs, k=3):
    selected_idx = random.sample(range(len(pop)), k)
    best_idx = min(selected_idx, key=lambda idx: costs[idx])
    return pop[best_idx][:]


def crossover(p1, p2):
    if random.random() > CROSSOVER_RATE:
        return p1[:], p2[:]
    # Lai ghep so hoc (Arithmetic Crossover) muot cho bien so thuc
    alpha = random.uniform(0.1, 0.9)
    c1 = [alpha * a + (1.0 - alpha) * b for a, b in zip(p1, p2)]
    c2 = [(1.0 - alpha) * a + alpha * b for a, b in zip(p1, p2)]
    return c1, c2


def mutate(chrom, gen):
    # Bien do dot bien giam dan theo the he de vua kham pha rong, vua tinh chinh sau
    scale = 0.25 * (1.0 - 0.7 * (gen / GENERATIONS))
    for i, (low, high) in enumerate(BOUNDS):
        if random.random() < MUTATION_RATE:
            delta = random.gauss(0, (high - low) * scale)
            chrom[i] = float(np.clip(chrom[i] + delta, low, high))
    return chrom


def main():
    print("[1/3] Dang khoi dong MATLAB Engine (doi tam 5-15 giay)...")
    t0 = time.time()
    eng = matlab.engine.start_matlab()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    eng.addpath(script_dir, nargout=0)
    print(f"--> Da ket noi MATLAB thanh cong sau {time.time() - t0:.1f}s!\n")

    print(f"[2/3] Bat dau chay GA (Quan the={POP_SIZE}, The he={GENERATIONS})...")
    pop = init_population()
    best_overall = None  # (cost, chrom, metrics)

    for gen in range(1, GENERATIONS + 1):
        costs = []
        metrics_list = []

        for chrom in pop:
            cost, metrics = evaluate_individual(eng, chrom)
            costs.append(cost)
            metrics_list.append(metrics)

        # Sap xep tu tot nhat (cost nho nhat) den xau nhat
        order = np.argsort(costs)
        gen_best_idx = order[0]
        gen_best_cost = costs[gen_best_idx]
        gen_best_chrom = pop[gen_best_idx][:]
        gen_best_metrics = metrics_list[gen_best_idx]

        if best_overall is None or gen_best_cost < best_overall[0]:
            best_overall = (gen_best_cost, gen_best_chrom, gen_best_metrics)

        kp, ki, kd = gen_best_chrom
        t_xl, pot, e_xl, st = gen_best_metrics
        print(
            f"Gen {gen:02d}/{GENERATIONS} | Cost={gen_best_cost:8.4f} | "
            f"Kp={kp:6.2f}, Ki={ki:6.2f}, Kd={kd:6.2f} | "
            f"t_xl={t_xl:.4f}s, POT={pot:.3f}%, e_xl={e_xl:.2e}, OnDinh={st}"
        )

        # Tao the he tiep theo (giu nguyen tinh hoa Elitism)
        next_pop = [pop[idx][:] for idx in order[:ELITISM_COUNT]]
        while len(next_pop) < POP_SIZE:
            p1 = tournament_select(pop, costs)
            p2 = tournament_select(pop, costs)
            c1, c2 = crossover(p1, p2)
            next_pop.append(mutate(c1, gen))
            if len(next_pop) < POP_SIZE:
                next_pop.append(mutate(c2, gen))
        pop = next_pop

# ================= IN KET QUA CHOT SO =================
    best_cost, (kp, ki, kd), (t_xl, pot, e_xl, st) = best_overall
    print("\n" + "=" * 68)
    print("[3/3] KET QUA TOI UU GA-PID (PYTHON <-> MATLAB)")
    print("=" * 68)
    print(f"  Kp tối ưu         : {kp:.4f}")
    print(f"  Ki tối ưu         : {ki:.4f}")
    print(f"  Kd tối ưu         : {kd:.4f}")
    print(f"  Thời gian xác lập : {t_xl:.4f} s")
    print(f"  Độ vọt lố (POT)   : {pot:.4f} %")
    print(f"  Sai số xác lập    : {e_xl:.6f} °C")
    print(f"  Khả năng ổn định  : {'ON DINH (1)' if st == 1 else 'MAT ON DINH (0)'}")

    uart_packet = f"GA,{kp:.2f},{ki:.2f},{kd:.2f},{t_xl:.4f},{pot:.3f},{e_xl:.4f},{st}\n"
    print(f"\n  Goi tin UART san sang gui STM32:\n  >>> {uart_packet.strip()}")
    print("=" * 68)

    # Xuat tu dong anh bieu do dap ung buoc tu MATLAB (luu ngay trong thu muc nay de gui Tu / lam bao cao)
    t_end = max(0.5, min(100.0, t_xl * 10.0))
    plot_path = os.path.join(script_dir, "dap_ung_ga_pid_matlab.png").replace("\\", "/")
    eng.eval(
        f"G = tf(1, [11.4 1]) * tf(250, [4.9 1]); "
        f"C = pid({kp}, {ki}, {kd}); "
        f"T = feedback(C * G, 1); "
        f"t = linspace(0, {t_end}, 1500); y = 150 * step(T, t); "
        f"fig = figure('Visible', 'off'); "
        f"plot(t, y, 'b-', 'LineWidth', 2); hold on; "
        f"plot([0 {t_end}], [150 150], 'r--', 'LineWidth', 1.5); grid on; "
        f"xlabel('Thoi gian (s)'); ylabel('Nhiet do (do C)'); "
        f"title(sprintf('Dap ung GA-PID: Kp=%.2f, Ki=%.2f, Kd=%.2f (txl=%.4fs, POT=%.3f%%)', {kp}, {ki}, {kd}, {t_xl}, {pot})); "
        f"legend('Dap ung lo nhiet', 'Setpoint 150 C', 'Location', 'southeast'); "
        f"saveas(fig, '{plot_path}'); close(fig);",
        nargout=0,
    )
    print(f"--> Da xuat anh bieu do MATLAB tai: {plot_path}")

    # Tu dong ban thong so GA vua tinh duoc xuong STM32 qua COM8
    try:
        with serial.Serial("COM11", 115200, timeout=2) as ser:
            time.sleep(0.5)
            ser.write(uart_packet.encode("utf-8"))
            print(">> PC da gui:", uart_packet.strip())
            reply = ser.readline().decode("utf-8", errors="ignore").strip()
            print("<< STM32 phan hoi:", reply if reply else "(Khong thay phan hoi - Kiem tra day TX/RX)")
    except Exception as e:
        print("Loi mo cong COM8 (kiem tra xem co phan mem nao dang chiem cong khong):", e)

    eng.quit()


if __name__ == "__main__":
    main()