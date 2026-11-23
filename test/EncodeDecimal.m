function pop = EncodeDecimal(par, sig, dec)
[N, d] = size(par);
for pop_index = 1:N
    gene_index = 1;
    for par_index = 1:d
        if par(pop_index,par_index) < 0
            pop(pop_index,gene_index) = 0;
        else
            pop(pop_index,gene_index) = 9;
        end
        gene_index = gene_index + 1;
        
        temp(par_index) = abs(par(pop_index, par_index))/10^dec(par_index);
        for count = 1:sig(par_index)
            temp(par_index) = 10*temp(par_index);
            pop(pop_index, gene_index) = temp(par_index) - rem(temp(par_index),1);
            temp(par_index) = temp(par_index) - pop(pop_index, gene_index);
            gene_index = gene_index + 1;
        end
    end
end
