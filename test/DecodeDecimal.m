function par = DecodeDecimal(pop, sig, dec)
[N, L] = size(pop);
d = length(sig);
par = zeros(N,d);
for pop_index = 1:N
    start_gene = 1;
    for par_index = 1:d
        for count = 1:sig(par_index)
            gene_index = start_gene + count;
            weight = dec(par_index) - count;
            par(pop_index, par_index) = par(pop_index, par_index) + (pop(pop_index, gene_index))*10^weight;
        end
        
        if pop(pop_index, start_gene) < 5
            par(pop_index, par_index) = -par(pop_index, par_index);
        end
        start_gene = start_gene + 1 + sig(par_index);
    end
end
