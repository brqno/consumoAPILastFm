# Consumo de API LastFm

Projeto para extrair dados da API LastFm, armazenar em um banco SQL Server e visualizar via Streamlit.

## Estrutura do projeto

- `main.py`: app Streamlit principal.
- `extract/extractAPI.py`: funções de extração e busca da API LastFm.
- `load/toSQL.py`: funções de conexão e leitura/escrita no SQL Server.
- `transform/toST.py`: funções de transformação e leitura de dados para o app.
- `archive_unused/`: scripts de depuração e testes arquivados.

## Organização recomendada

- `archive_unused/` contém arquivos auxiliares que não fazem parte do fluxo principal.
- O app principal usa apenas `extract/`, `load/` e `transform/`.

## Dependências

- streamlit
- pandas
- requests
- pyodbc
- sqlalchemy
- python-dotenv

## Uso

1. Crie um arquivo `.env` na raiz do projeto com as chaves necessárias. Exemplo em `.env.example`.
2. Defina as variáveis de ambiente:
   - `LASTFM_API_KEY`
   - `LASTFM_API_SECRET`
   - `LASTFM_USER`
   - `DB_SERVER`
   - `DB_DATABASE`
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Execute o app Streamlit:
   ```bash
   streamlit run main.py
   ```
