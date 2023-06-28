# Sobre

Assembler para o conjunto de instruções hipotético usado na disciplina de Arquitetura de Computadores do IFPR-Paranavaí.

# Compilando

Para compilar, apenas use o **make**.

# Running

O binário do compilador é o **pasm**.

# Sobre o conjunto de instruções

A especificação do conjunto de instruções pode ser consultada na aula que ministro, em **docs/12-instrucoes-codificacao.pdf**.

Importante apenas ressaltar os seguintes pontos:

- 8 registradores de propósito geral

- Os registradores são de 16 bits

- Cada palavra da memória também tem 16 bits, de forma que o endereço 0 (zero) referencia os bytes 0 e 1, o endereço 1 referencia os bytes 2 e 3, e assim por diante.

# Sobre o código gerado

O linker irá buscar pelo símbolo **_start**, que deverá referenciar a instrução inicial do código.

O início do código gerado ficará da seguinte forma:

- Endereço 0 (zero): conterá o valor 0 (zero)

- Endereço 1: conterá uma instrução jump para o símbolo **_start**

Dessa forma, um simulador para tal arquitetura deverá setar como endereço inicial do registrador **pc** o endereço **1**.


# RUNING

Para rodar o projeto antes temos que
- compilar os arquivos asm em .bin (já estão compilados)
- executar o make na raiz (já estão compilados)

após termos o projeto completo, basta executar
 python2 pysim.py

Comandos:

**bye** -> sair do sitema

**tasks** -> apresenta as tasks rodando

**run** -> roda a função requisitada em um novo processo

```run print.bin```

**kill**-> mata o processo informado

```kill print.bin```