import json
import os
import re
import time
from bs4 import BeautifulSoup
import requests

# -------------------------------------------------------------------------
# CONFIGURAÇÃO COM BASE NO SEU SNAPSHOT DE ABRIL DE 2026
# -------------------------------------------------------------------------
DOMINIO_WIKI = "digitalmastersworld.wiki.gg"
TIMESTAMP_ALVO = "20260413191242"  # Data exata que você forneceu
REQUEST_TIMEOUT = 90
MAX_RETRIES = 5
TEMPO_ESPERA = 5.0
LIMITE_PAGINAS_POR_EXECUCAO = 20
SALVAR_A_CADA = 10
ARQUIVO_PROGRESSO = "dmw_progresso.json"
ARQUIVO_FINAL = "banco_completo_dmw.json"


def pagina_eh_relevante(url):
    """Mantém apenas páginas reais de conteúdo da wiki, ignorando APIs, assets e challenge pages."""
    if not isinstance(url, str):
        return False

    url = url.lower().strip()
    if not url:
        return False

    if not (url.startswith("http://") or url.startswith("https://")):
        return False

    if "digitalmastersworld.wiki.gg" not in url:
        return False

    if any(
        termo in url
        for termo in [
            "api.php",
            "/ads.txt",
            "/.well-known/",
            "/cdn-cgi/",
            "cloudflare",
            "challenge-platform",
            "main.js",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".woff",
            ".woff2",
            ".css",
            ".js",
            "special:",
            "talk:",
            "user:",
            "category:",
            "action=",
            "file:",
            "raw=1",
        ]
    ):
        return False

    if "/wiki/" in url:
        return True

    return url in {f"https://{DOMINIO_WIKI}/", f"http://{DOMINIO_WIKI}/"}


def obter_paginas_da_wiki(dominio, timestamp):
    """Consulta a API do Wayback Machine para listar todos os links salvos próximos à data informada."""
    print(
        f"🔍 Mapeando todas as páginas internas de '{dominio}' a partir do snapshot {timestamp}..."
    )

    cdx_url = (
        "https://web.archive.org/cdx/search/cdx?"
        f"url={dominio}/*&output=json&fl=original,timestamp&filter=statuscode:200"
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            print(f"📡 Tentativa {tentativa}/{MAX_RETRIES} na API do Wayback...")
            response = requests.get(cdx_url, headers=headers, timeout=REQUEST_TIMEOUT)
            print(f"📡 Resposta da API: status {response.status_code}")
            response.raise_for_status()

            dados = response.json()
            if not isinstance(dados, list) or len(dados) <= 1:
                print("⚠ Nenhuma página interna localizada no histórico.")
                return []

            urls_filtradas = {}

            for linha in dados[1:]:
                if not linha or len(linha) < 2:
                    continue

                url_original = linha[0]
                if not isinstance(url_original, str):
                    continue

                if not pagina_eh_relevante(url_original):
                    continue

                url_wayback = f"https://web.archive.org/web/{timestamp}/{url_original}"
                urls_filtradas[url_original] = url_wayback

            print(
                f"✔ Sucesso! Encontradas {len(urls_filtradas)} páginas da Wiki para processar."
            )
            return list(urls_filtradas.values())

        except requests.exceptions.Timeout as e:
            print(f"⏳ Timeout na API do Wayback (tentativa {tentativa}/{MAX_RETRIES}): {e}")
            if tentativa == MAX_RETRIES:
                print("❌ A API do Wayback demorou demais e não respondeu a tempo.")
                return []
            time.sleep(2)
        except Exception as e:
            print(f"❌ Erro ao listar URLs: {e}")
            return []

    return []


def extrair_atributos_tabela(url):
    """Acessa a página arquivada e extrai os dados das tabelas de atributos."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if res.status_code == 429:
                print(f"⚠️ Bloqueio detectado pelo servidor (429) em: {url}")
                return None
            if res.status_code in {403, 503}:
                print(f"⚠️ Acesso negado ou indisponível em: {url} (status {res.status_code})")
                return None
            if res.status_code != 200:
                return []

            soup = BeautifulSoup(res.text, "html.parser")
            conteudo_principal = soup.find(id="mw-content-text") or soup.find(
                "div", class_="mw-parser-output"
            )
            if not conteudo_principal:
                return []

            tabelas = conteudo_principal.find_all("table", class_="wikitable")
            dados_coletados = []

            for tabela in tabelas:
                cabecalhos = [
                    th.text.strip().lower().replace(" ", "_")
                    for th in tabela.find_all("th")
                ]
                linhas = tabela.find_all("tr")

                for linha in linhas:
                    celulas = linha.find_all("td")
                    if not celulas:
                        continue

                    item_info = {}
                    for i, celula in enumerate(celulas):
                        if i < len(cabecalhos):
                            chave = cabecalhos[i]
                            valor = re.sub(r"\s+", " ", celula.text).strip()
                            item_info[chave] = valor

                    if item_info:
                        nome_pagina = url.split("/wiki/")[-1]
                        item_info["origem_pagina"] = nome_pagina
                        dados_coletados.append(item_info)

            return dados_coletados
        except requests.exceptions.Timeout:
            print(f"⏳ Timeout em {url} (tentativa {tentativa}/{MAX_RETRIES})")
            if tentativa == MAX_RETRIES:
                return None
            time.sleep(5)
        except requests.exceptions.RequestException as e:
            print(f"❌ Falha de rede em {url}: {e}")
            return None
        except Exception:
            return []

    return None


def ordenar_paginas(paginas):
    """Prioriza páginas de conteúdo real e ignora páginas de busca/auxiliares antes de processar."""
    def prioridade(url):
        u = url.lower()
        score = 0
        if "/wiki/" in u:
            score += 100
        if "speciale:ricerca" in u or "/special/" in u:
            score -= 200
        if u.endswith("/"):
            score += 10
        if "search" in u:
            score -= 50
        if "?" in u:
            score -= 20
        return score

    return sorted(paginas, key=lambda url: (-prioridade(url), url))


def salvar_json(path, dados):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)


def carregar_progresso(path):
    if not os.path.exists(path):
        return [], set()

    try:
        with open(path, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados.get("itens", []), set(dados.get("processadas", []))
    except Exception:
        return [], set()


if __name__ == "__main__":
    lista_paginas = ordenar_paginas(obter_paginas_da_wiki(DOMINIO_WIKI, TIMESTAMP_ALVO))
    banco_de_dados, processadas = carregar_progresso(ARQUIVO_PROGRESSO)

    if lista_paginas:
        print(
            "🚀 Iniciando extração em lote em modo seguro. O script vai processar blocos, salvar progresso e continuar automaticamente."
        )

        paginas_pendentes = [url for url in lista_paginas if url not in processadas]
        total_geral = len(paginas_pendentes)

        if total_geral == 0:
            print("✅ Nenhuma página pendente. Tudo foi processado anteriormente.")
            salvar_json(ARQUIVO_FINAL, banco_de_dados)
            raise SystemExit

        bloco_atual = 0
        while paginas_pendentes:
            bloco = paginas_pendentes[:LIMITE_PAGINAS_POR_EXECUCAO]
            paginas_pendentes = paginas_pendentes[LIMITE_PAGINAS_POR_EXECUCAO:]
            bloco_atual += 1
            total_bloco = len(bloco)

            print(f"\n📦 Bloco {bloco_atual} com {total_bloco} páginas.")

            for index, url_pagina in enumerate(bloco, start=1):
                if url_pagina in processadas:
                    print(f"[skip] Página já processada: {url_pagina}")
                    continue

                print(f"[{index}/{total_bloco}] Extraindo de: {url_pagina}")
                dados_pagina = extrair_atributos_tabela(url_pagina)

                if dados_pagina is None:
                    print("⚠️ Falha temporária nesta página. Pulando para a próxima e preservando progresso.")
                    salvar_json(ARQUIVO_PROGRESSO, {"itens": banco_de_dados, "processadas": sorted(processadas)})
                    time.sleep(TEMPO_ESPERA)
                    continue

                if dados_pagina:
                    banco_de_dados.extend(dados_pagina)
                    processadas.add(url_pagina)

                if len(banco_de_dados) % SALVAR_A_CADA == 0:
                    salvar_json(ARQUIVO_PROGRESSO, {"itens": banco_de_dados, "processadas": sorted(processadas)})
                    salvar_json(ARQUIVO_FINAL, banco_de_dados)
                    print(f"💾 Progresso parcial salvo: {len(banco_de_dados)} registros.")

                time.sleep(TEMPO_ESPERA)

            salvar_json(ARQUIVO_PROGRESSO, {"itens": banco_de_dados, "processadas": sorted(processadas)})
            salvar_json(ARQUIVO_FINAL, banco_de_dados)

            if not paginas_pendentes:
                break

            print("⏳ Próximo bloco em 10 segundos...")
            time.sleep(10)

        print(
            f"\n🎉 Execução concluída ou interrompida com segurança. Arquivo final: '{ARQUIVO_FINAL}' com {len(banco_de_dados)} registros."
        )
