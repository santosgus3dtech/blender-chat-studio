# Blender Chat Studio

[English / README principal](README.md) · Português (Brasil)

[![CI](https://github.com/santosgus3dtech/blender-chat-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/santosgus3dtech/blender-chat-studio/actions/workflows/ci.yml)

Uma base pública adequada para portfólio, destinada à modelagem 3D por conversa
com Blender e MCP. Esta primeira versão publica o núcleo real de execução, não
um chat de IA hospedado: um cliente MCP envia uma cena completa, um processo
restrito no Linux executa o Blender e os artefatos validados retornam com
medições de geometria e hashes.

**Estado:** núcleo de execução disponível; uma interface de chat independente e
uma demonstração pública interativa são os próximos marcos. Não há endpoint
público de inferência, sessão de conta incluída, integração com impressora ou
fatiamento automático.

## O que funciona

- Ferramentas MCP locais por stdio: `worker_health` e `execute_blender`.
- Política AST conservadora e um processo Blender separado, sem acesso root ou rede.
- Cena nova a cada execução; limites de tempo, memória, processos e tamanho da saída.
- Exportações GLB, STL, BLEND, PNG e JSON; validação de toda a saída e hashes SHA-256.
- Três scripts originais de cenas determinísticas para exemplos reproduzíveis.
- Testes e CI sem provedor. Esta versão não precisa de chave de API.

Os exemplos são **scripts escritos pelo autor**, não uma comprovação de geração
por IA. As verificações de topologia e dimensões não certificam resistência
mecânica, união de sólidos, tolerâncias ou viabilidade de impressão física. Os
exemplos com vários objetos expõem deliberadamente essa limitação.

## Exemplos originais

| Cubo com chanfros | Guia de cabos | Organizador de mesa |
| --- | --- | --- |
| ![Cubo com chanfros](examples/exports/beveled-cube/preview.png) | ![Guia de cabos](examples/exports/cable-guide/preview.png) | ![Organizador de mesa](examples/exports/desk-organizer/preview.png) |
| [GLB](examples/exports/beveled-cube/model.glb) / [STL](examples/exports/beveled-cube/model.stl) | [GLB](examples/exports/cable-guide/model.glb) / [STL](examples/exports/cable-guide/model.stl) | [GLB](examples/exports/desk-organizer/model.glb) / [STL](examples/exports/desk-organizer/model.stl) |

São exportações reais do Blender a partir dos três scripts incluídos, não
capturas de uma interface de chat concluída. As dimensões e limitações estão
registradas na [verificação](docs/VERIFICATION.md).

## Início rápido

Python 3.12+ e [uv](https://docs.astral.sh/uv/) são suficientes para os testes de sintaxe:

```sh
uv sync --locked --extra dev
uv run --locked pytest -q
uv run --locked blender-studio validate examples/beveled-cube.py
```

A geração real requer Docker com **contêineres Linux**, inclusive no Windows:

```sh
docker compose --profile tools build
docker compose up -d --wait worker
docker compose run --rm tools health
docker compose run --rm tools run examples/beveled-cube.py
docker compose run --rm tools run examples/cable-guide.py
docker compose run --rm tools run examples/desk-organizer.py
docker compose run --rm -T --entrypoint python tools -m studio.smoke
```

Os resultados são gravados no volume nomeado `exports`, sob um novo UUID de
execução. Eles não são gravados no diretório do código-fonte. Quando necessário,
copie para fora resultados explicitamente selecionados com `docker cp`, a partir
de um contêiner tools mantido. `docker compose stop` interrompe o processo de
trabalho deste projeto sem excluir as exportações.

Para um cliente MCP local, execute a imagem tools por meio do Compose, sem porta publicada:

```sh
docker compose run --rm -T --entrypoint blender-studio-mcp tools
```

Inicie o processo de trabalho primeiro. O host MCP fornece seu próprio
modelo/provedor; este servidor não lê arquivos `.env` nem se conecta a um
provedor de modelos. Não exponha suas ferramentas de execução como um serviço
anônimo na internet.

## Arquitetura

```text
Trusted local MCP host or deterministic CLI
                |
     MCP stdio / execution adapter
                |
   size-bounded private Unix socket
                |
   networkless, read-only Linux worker
                |
     fresh background Blender process
                |
 GLB / STL / BLEND / PNG / geometry report
```

As coordenadas de cena, os arquivos STL e os relatórios usam **milímetros**.
GLB usa **metros**. A política de sintaxe é uma defesa em profundidade, não uma
sandbox Python. O isolamento em contêiner é obrigatório para a execução real.
Consulte [segurança](SECURITY.md) e [arquitetura](docs/ARCHITECTURE.md).

## Tecnologias

Python, Blender/bpy, Model Context Protocol (MCP), asyncio, Docker Compose,
pytest, Ruff, uv e GitHub Actions. O chat/visualizador planejado usará React,
TypeScript e Three.js; eles não estão incluídos nesta primeira versão.

## Roteiro de desenvolvimento

1. Adicionar uma reprodução pública de chat em modo de leitura, visualizador Three.js e download dos exemplos originais.
2. Demonstrar a criação inicial, uma revisão solicitada e a comparação lado a lado.
3. Adicionar um adaptador local de provedor configurado explicitamente, orçamentos, cancelamento e histórico de versões.
4. Considerar geração online somente após revisar autenticação, cotas e execução isolada de tarefas.

A edição operacional permanece separada. Este repositório começa com um
histórico Git novo e não contém dados operacionais nem fluxo de autenticação
de contas.

## Licença

MIT para o código original e os scripts de exemplo deste repositório. Blender
e dependências mantêm suas respectivas licenças; o Blender é instalado a partir
do Debian, não copiado para este repositório. Consulte as
[notas de terceiros](THIRD_PARTY_NOTICES.md).
