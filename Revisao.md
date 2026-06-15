





# 1. CPU - Unidade Computacional de Processamento 
	 
	 Triade de Processamento :
		 1. U.C. : Unidade de Controle
			 - Decodifica instrucoes - Opcode [ Codigo de Operacao ] 
			 - Emite Sinais - Gera sinais (Eletricos) para ativar a ULA OU Abrir portas para movimentacao de dados.
			 - Gerencia o Fluxo de dados entre o Processador - Memoria - E/S
			 - Bsuca Instrucao da Memoria 
			 - CLOCK - Sincroniza o envio dos sinais para garantir que tudo acontenca no tempo exato
				 > Def. : CLOCK e um sinal de onda quadrada, gerado por um cristal de quartzo que sincroniza todas as operacoes da CPU.
				 > Freq.(Hz) : 3GHz = 3*10^9 oscilacoes / segundo 
				 > Cada operacao consome um ou mais ciclos 
					 Operacoes: 
						 Buscar 
						 Codificar 
						 Executar 
				> O Clock garante que todos os sinais elec. se estabilizem antes da proxima etapa
			



		2. U.L.A. : Unidade Logica / Aritmetica
			- Realiza Calculos 
			- Decisoes Logicas 
			- Flags e Sinalizadores - Status Register:
				> Z - Zero Flag =  Algebra Booleana - Comparacoes 
					# SHIFT Operacoes de Deslocamento :
						(1) Shift Left = Multiplica por 2;
						(2) Shift Right = Divide por 2;
						*SHIFT move bits dentro de uma palavra*
						*Vital para matematica rapida / CRIPTOGRAFIA / Processamento Grafico*
						*Logico = Preenche com zeros*
						*Aritmmetico = Preserva sinal {Numeros Negativos}*
				> V - Overflow = OUTPUT maior que a capacidade do registrador
				> N - Negative = O bit mais significativo e o 1
				> C - Carry = Transporta o bit mais significativo.
				*OBS.: Flags sao usados pela UC para tomar decisoes de desvio condicional [Branches]*
			- # Somador [ ADDER ] =  32x or 64x 
			- # Multiplexador [ MUX ] = Seleciona qual resultado das operacoes internas sera enviado para o output
			
			- *Circuito Combinatorio* = Saida depende apende dos inputs atuais. 
					> A ULA nao tem memoria interna
									
			 - *Tecnologias de Implementacao*
				 > P.L.A. [ Programmable Logic Array ] = Uma matriz de portas AND / OR programaveis
					 *Permite flexibilidade no design de funcoes booleanas customizadas*
				 > F.P.G.A [ Field-Programmable Gate Array ] = Blocos logicos con
					*Permite criar processadores 'sob medida' apos fabricacao*




				
				
		3. Registradores 
			- Memoria Interna de Altissima Velocidade para Armazenamento Temporario imediato
			- P.C. : Contador de Programa
				> Armazena o endereco da proxima instrucao a ser buscada.
				> E o Ponteiro 
			- I.R.: Registrador de Instrucao 
				> Armazena a instrucao que esta sendo exec. no momento
				> UC le o OPCODE
			- M.A.R. / R.E.M. : Memory Address Register 
				> 	Especifica o endereco de memoria onde a CPU quer ler ou escrever um dado.
			- M.B.R. / R.D.M. : Memory Buffer Register 
				> Contem o valor lido da memoria ou o valor a ser gravado nela.
			- OBS.: Os registradores estao no topo da hierarquia de memoria 
				> Sao mais rapidos e menores 
				> Localizam-se dentro da CPU
				> Eficiencia da CPU = Velocidade de troca entre os Registradores e a ULA




				
	Ciclo Eterno Da Computacao [ Ciclo De Instrucao ] : Todo software , navegador , SO e uma sequencia de instrucoes. 
		 1. Busca [ Fetch ] :
			 - CPU verifica o PC para endereco de instrucao
			 - Endereco e enviado para a memoria
			 - Instrucao guardada no IR
			 - PC incrementado
		 2. Decodificacao [ Decode ] :
			 - UC analisa o Opcode 
			 - Identica a operacao
			 - Localiza dados necessarios
		 3. Execucao [ Exec ] :
			 - UC envia sinais para ULA 
			 - ULA processa dados 
		4. Escrita [Write Back ] :
			- Resultado gravado em Registrador OU Memoria
			- CPU verifica Interrupcoes 
			- Return Loop to Fetch 
		*A Velocidade do LOOP define o poder do processamento*
		
		# Pipeline - Cascata de Instrucoes'Linha de montagem industrial' = Enquanto uma instrucao e executada, a proxima ja esta sendo decodificada e uma terceira esta sendo buscada.
			> Resultado : Aumento exponencial na vazao sem necessariamente aumentar o clock
			




# 2.  Arquitetura de Memoria : Hierarquia de Dados
	*Gargalo de Von Neumann* - Diferenca entre as velocidades de processamento de dados da CPU e seu armazenamento permanente (HD / SSD)
	RAM [Random Access Memory] - Solucao para o Gargalo de Von Neumann  
	
	1. Piramide Hierarquica de Memoria 
		- Registradores
		- Cache
		- Memoria Principal
		- Disco Magnetico 
		- Pen-Drive / Disco Optico 
	OBS.01: Regra de Ouro = Ao descer pela piramide
		- Custo por Bit - Diminui 
		- Capacidade -  Aumenta
		- Tempo de Acesso - Aumenta 
		- Frequencia de Acesso (CPU) - Diminui
	OBS.02: 
		- Memoria Volatil = Perde dados sem energia 
		- Memoria Nao-Volatil = NAO perde dados sem energia
	
	2. Cache [ SRAM ] -  Memoria Escrava
		- Pequena + Ultrarapida
		- Localidade Temporal = Se um dado foi usado recentemente, provavelmente ser usado novamente 
		- Localidade Espacial = Se um 'endereco' foi acessado, provavelmente 'enderecos' vizinhos tambem sejam acessados. Ex.: Vetores 		
		- SRAM = *Static* - Mantem o dado enquanto houver energia. *Sem REFRESH*
			> Velocidade: Tempo de acesso proximo ao ciclo da CPU 
			> Densidade: Baixa
			> Custo: Alto custo por Bit
			> Uso exclusivo em Cache (L1 , L2 , L3)
	
	3. Memoria Principal [ DRAM - Dynamic RAM ] : Atua como ponte intermediaria entre o HD e o CPU.
		- Estrutura Fisica = 1 Transistor + 1 Capacitor / Bit
		- Refresh (Dinamico) = O capacitor armazena cargas eletricas (0 or 1) por custo energetico, portanto um circuito deve ler e regravar os dados milhares de vezes por segundo 
			> Maior latencia
			> Alta densidade 
			> Baixo Custo
			
		- SDRAM x DDR
			> SDRAM [Synchronous DRAM] - Sincroniza a transferencia de dados com o clock do sistema, eliminando estados de espera.
			> DDR - Transfere dados em ambas as bordas do clock 
				Dobra a taxa de transferencia teorica sem aumentar a frequencia 
				Aumentam a Velocidade
				Reduzem o Consumo energetico
		
	4. Memoria Nao-Volatil : ROM [Ready Only Memory] - Retem Dados sem consumo de energia.
		- Essencial para o /boot e Firmware (BIOS / UEFI)
		- ROM - Gravada na fabrica [ Imutavel ]
		- PROM - Programavel uma vez
		- EPROM - Apagavel por luz ultravioleta [Janela de Quartzo]
		- EEPROM - Apagavel eletronicamente byte a byte 
			*Flash Memory* = Rev. NVRAM , permite o apagamento eletrico em blocos, tornando-a muito mais rapida
				> Flash NOR - Acesso aleatorio a bytes ; Execucao de Codigos (Firmware)
				> Flash NAND - Read / Write em blocos ; Maior Densidade, menor custo ; Ideal para armazenamento em massa