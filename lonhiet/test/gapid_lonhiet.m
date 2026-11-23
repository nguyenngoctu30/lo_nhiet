clear all
%clc;
%clear all
%rand('state',sum(100*clock));
%q1 = 1;
q2 = 0.2;
% St%op condition
% Stall generations is the number of iterations with no improvement in the best fitness value
max_generation = 100;
max_stall_generation = 50;  
epsilon = 0.000001;
% Parameter
pop_size = 20;          % population size
npar = 3;               % 3 parameters a1, a2, a3
range = [ 0  0  0;...       % min value a1, a2, a3
         160 160 160];     % max value a1, a2, a3
dec = [3  3  2];        % posiition of decimal point
sig = [5  5  5];        % 5 gen
cross_prob = 0.9;       % probability of cross
mutate_prob = 0.1;      % -------------- mutation
elitism = 1;            % keep the best individual
% par = range*rand(pop_size, npar);
par = InitPop(pop_size, npar, range);                                       %
stop_condition = 0;
generation = 0;
stall_generation = 0;
for pop_index = 1:pop_size,
    Kp = par(pop_index,1);  % a1
    Ki = par(pop_index,2);  % a2
    Kd = par(pop_index,3);  % a3
    sim('pid_lonhiet');      % run PBCsim.slx
    J = (e)'*(e) +q2*(u)'*(u);      % criterion
    fitness(pop_index) = 1/(J+eps); % min
end
[bestfit0, bestchrom] = max(fitness);
 Kp0=par(bestchrom,1);
Ki0=par(bestchrom,2);
Kd0=par(bestchrom,3);
J0=1/bestfit0-0.0001;

while ~stop_condition,
    generation = generation + 1;
    pop = EncodeDecimal(par, sig, dec);
    parent = SelectLinearRanking(pop, fitness, 0.5, elitism, bestchrom);    %
    child = CrossTwoPoint(parent, cross_prob, elitism, bestchrom);          %
    pop = MutateUniform(child, mutate_prob, elitism, bestchrom);            %
    par = DecodeDecimal(pop, sig, dec);                                     %
    
    for pop_index = 1:pop_size,
        Kp = par(pop_index,1);  % a1
        Ki = par(pop_index,2);  % a2
        Kd = par(pop_index,3);  % a3
        sim('pid_lonhiet');      % run PBCsim.slx
         J = (e)'*(e) +q2*(u)'*(u);      % criterion
         fitness(pop_index) = 1/(J+eps);
    end
    [bestfit(generation), bestchrom] = max(fitness);
    Kpth(generation)=par(bestchrom,1);
Kith(generation)=par(bestchrom,2);
Kdth(generation)=par(bestchrom,3);
    if generation == max_generation
        stop_condition = 1;
    elseif generation > 1
        if abs(bestfit(generation) - bestfit(generation - 1)) < epsilon
            stall_generation = stall_generation + 1;
            if stall_generation == max_stall_generation, 
                stop_condition = 1;
            end
        else
            stall_generation = 0;
        end
    end
end
plot(1./bestfit,'k')
figure(2)
plot(bestfit,'k')
figure(3)
plot(Kpth,'k')
figure(4)
plot(Kith,'k')
figure(5)
plot(Kdth,'k')
Kp0
Ki0
Kd0
J0
Kp = par(bestchrom,1)  % a1
Ki = par(bestchrom,2)  % a2
Kd = par(bestchrom,3)  % a3
J=1/bestfit(end)
sim('pid_lonhiet');     % run PBCsim.slx
