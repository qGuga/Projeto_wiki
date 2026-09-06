# DMW Wiki Data Pipeline

Projeto de coleta, organização e visualização de dados da wiki **Digital Masters World**.

## Visão geral

Este projeto reúne uma página web estática para consulta do conteúdo coletado e scripts Python para:

- localizar páginas históricas da wiki usando o Wayback Machine;
- filtrar páginas de conteúdo e ignorar assets, APIs e páginas auxiliares;
- extrair tabelas HTML em registros estruturados;
- salvar o progresso para permitir execuções incrementais;
- consolidar os dados em JSON para uso na interface.

## Estrutura

| Arquivo | Função |
| --- | --- |
| `Site_wiki.html` | Interface web estática para explorar as linhas de evolução e os dados reunidos. |
| `wz.py` | Coleta, filtragem, extração e persistência do conteúdo da wiki. |
| `_collect_images.py` | Apoio à coleta de imagens relacionadas ao projeto. |
| `banco_completo_dmw.json` | Banco consolidado gerado pela coleta. |
| `dmw_progresso.json` | Estado intermediário para retomada do processamento. |

## Execução local

1. Crie um ambiente Python e instale as dependências usadas pelos scripts:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install beautifulsoup4 requests
   ```

2. Execute a coleta:

   ```powershell
   python wz.py
   ```

3. Abra `Site_wiki.html` no navegador para consultar a interface.

> A coleta depende da disponibilidade da fonte externa e deve respeitar os termos de uso, limites de requisição e direitos sobre o conteúdo original.

## Privacidade e publicação

Este repositório não deve conter tokens, cookies, credenciais ou dados pessoais. O conteúdo coletado pertence à fonte original; esta publicação documenta o trabalho técnico de organização e visualização.

## Licença

Código e materiais originais deste projeto são disponibilizados com **todos os direitos reservados**. Nenhuma cópia, redistribuição, modificação ou uso comercial é autorizado sem permissão expressa do autor. Consulte `LICENSE`.