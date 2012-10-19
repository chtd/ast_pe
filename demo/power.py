# -*- encoding: utf-8 -*-

import sys
sys.path.append('.')

from ast_pe.decorators import inline


@inline                                                                
def power(x, n):                                                       
    if not isinstance(n, int) or n < 0:                                
        raise ValueError('Base should be a positive integer')          
    elif n == 0:                                                       
        return 1                                                       
    elif n % 2 == 0:                                                   
        v = power(x, n / 2)                                            
        return v * v                                                   
    else:                                                              
        return x * power(x, n - 1) 

from ast_pe import specialized_fn
PRINT_AST = True

power_5 = specialized_fn(power, globals(), locals(), n=5)

print power_5(2)

power_27 = specialized_fn(power, globals(), locals(), n=27)

print power_27(2)
