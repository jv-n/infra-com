# Transferência de Arquivos (Cliente-Servidor)

Sistema simples de envio de arquivos entre um cliente e um servidor usando Sockets.

## Como Usar

1. Inicie o servidor:  
   python servidor.py

2. Execute o cliente:  
   python cliente.py

## Envio de Arquivos  

Para enviar um arquivo diferente, edite "FILE_TO_SEND" no cliente.py.  
Os arquivos "data.jpg" e "data.txt" devem estar na mesma pasta do código.

## Estrutura  

projeto/  
 ├── servidor.py  
 ├── cliente.py  
 ├── data.txt  
 ├── data.jpg  
 └── README.txt  

## Observações  

- Execute o servidor antes do cliente.  
- Para enviar outro arquivo, basta alterar "FILE_TO_SEND".  
