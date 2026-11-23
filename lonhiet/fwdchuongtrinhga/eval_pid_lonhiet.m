function [t_xl, pot, e_xl, stable, max_re] = eval_pid_lonhiet(Kp, Ki, Kd)
    G = tf(1, [11.4 1]) * tf(250, [4.9 1]);
    C = pid(double(Kp), double(Ki), double(Kd));
    T = feedback(C * G, 1);

    p = pole(T);
    max_re = max(real(p));

    % Neu mat on dinh hoac cuc qua sat truc ao -> tra ve max_re de GA phat mem
    if ~isstable(T) || max_re >= -1e-4
        t_xl = 100.0;
        pot = 100.0;
        e_xl = 150.0;
        stable = 0;
        return;
    end

    t = linspace(0, 100, 1500);
    y = 150 * step(T, t);
    info = stepinfo(y, t, 150);

    t_xl = info.SettlingTime;
    if isnan(t_xl) || isinf(t_xl), t_xl = 100.0; end
    pot = info.Overshoot;
    if isnan(pot) || isinf(pot), pot = 100.0; end
    e_xl = abs(150 - y(end));
    stable = 1;
end