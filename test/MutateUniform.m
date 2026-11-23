function pop = MutateUniform(pop, mutate_prob, elitism, bestchrom)
[N, L] = size(pop);
newpop = pop;
for pop_index = 1:N
    if (elitism == 0) || (elitism == 1 && pop_index ~= bestchrom)
        for gene_index = 1:L
            if mutate_prob > rand
                rand_gene = 10*rand;
                while (pop(pop_index, gene_index) == rand_gene - rem(rand_gene,1)||rand_gene == 10)
                    rand_gene = 10*rand;
                end
                newpop(pop_index, gene_index) = rand_gene - rem(rand_gene, 1);
            end
        end
    end
end
