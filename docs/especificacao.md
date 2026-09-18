# Sistema de Integração Recepção-SGG

Sep 17, 2026 · @Someone

## 1. Visão Geral e Objetivo

Este documento descreve o sistema de **totem/tablet de autoatendimento
para recepção**, que se integra à API do SGG para automatizar a triagem
e o check-in de pacientes, eliminando a necessidade de um recepcionista
realizar manualmente a busca e a atualização de status de cada
agendamento.

**Objetivo do sistema:** permitir que o próprio paciente, ao chegar à
unidade, confirme sua presença em um tablet fixado na recepção —
informando apenas o CPF — e tenha seu agendamento automaticamente
localizado e movido para o status "aguardando" no SGG, ou, na ausência
de agendamento prévio, tenha um novo agendamento criado automaticamente
na agenda de encaixe definida pelo administrador.

**Problema que resolve:** reduz filas e tempo de espera, elimina erro
humano na atualização de status, e libera a recepção para atendimentos
que realmente exigem intervenção humana (ex.: paciente não cadastrado no
SGG).

## 2. Escopo do Sistema

### Dentro do escopo

-   Aplicativo web (tablet, tela cheia/kiosk) para autoatendimento do
    paciente na recepção.

-   Sincronização automática (via API do SGG) das **agendas** e **locais
    de atendimento** cadastrados.

-   Painel administrativo para:

    -   Selecionar quais agendas do SGG serão consultadas pelo totem.

    -   Definir, para cada agenda monitorada, a **agenda de
        encaixe/fallback** para onde o paciente será direcionado caso
        não haja agendamento localizado.

-   Fluxo de autoatendimento com seleção de tipo de atendimento
    (Preferencial / Normal).

-   Busca de paciente por CPF na base do SGG.

-   Confirmação de dados cadastrais do paciente na tela.

-   Atualização de status do agendamento no SGG (Agendado → Aguardando)
    quando o agendamento é localizado.

-   Criação automática de agendamento no SGG (na agenda de encaixe
    definida) quando não há agendamento prévio, usando o cadastro já
    existente do paciente.

-   Tratamento de erro quando o paciente não está cadastrado no SGG, com
    mensagem orientando o direcionamento à recepção física.

### Fora do escopo (nesta fase)

-   Cadastro de novos pacientes pelo totem (o paciente precisa já
    existir no SGG).

-   Emissão de senha/impressão de ticket físico.

-   Relatórios analíticos de fluxo/tempo de espera (pode ser um MVP+
    futuro).

-   Integração com outros sistemas além do SGG.

## 3. Fluxo de Funcionamento

**3.1 Sincronização em segundo plano**

-   O sistema consulta periodicamente a API do SGG e mantém em cache
    local as agendas e locais de atendimento ativos.

-   O administrador seleciona, em painel próprio, quais agendas o totem
    deve considerar ao buscar agendamentos, e associa a cada uma uma
    agenda de encaixe (fallback).

**3.2 Tela inicial (tablet)**

1.  Paciente toca em **Preferencial** ou **Normal**.

2.  Sistema exibe campo para digitação do **CPF**.

**3.3 Busca do agendamento** 3. Sistema consulta a API do SGG pelo CPF
informado, dentro das agendas configuradas para consulta. 4. **Se
paciente não está cadastrado no SGG:** exibe mensagem de erro orientando
a se dirigir à recepção. Fim do fluxo. 5. **Se cadastrado**, sistema
exibe os dados cadastrais (nome, e demais campos relevantes) para o
paciente confirmar se estão corretos.

**3.4 Com agendamento encontrado** 6. Sistema atualiza, via API, o
status do agendamento de **Agendado** para **Aguardando**. 7. Exibe
confirmação de check-in realizado.

**3.5 Sem agendamento encontrado** 6. Sistema cria, via API, um novo
agendamento na **agenda de encaixe** configurada para aquela agenda de
origem, vinculado ao cadastro do paciente no SGG. 7. Exibe confirmação
de check-in realizado.

**3.6 Retorno à tela inicial** 8. Após a confirmação (ou erro), o tablet
retorna automaticamente à tela inicial após alguns segundos, pronto para
o próximo paciente.

## 4. Requisitos Funcionais

| \#   | Requisito                                                                                                                                       |
|------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| RF01 | O sistema deve sincronizar automaticamente as agendas e locais de atendimento cadastrados no SGG via API.                                       |
| RF02 | O administrador deve poder selecionar, em um painel próprio, quais agendas do SGG serão consultadas pelo totem.                                 |
| RF03 | O administrador deve poder configurar, para cada agenda monitorada, uma agenda de encaixe (fallback) de destino.                                |
| RF04 | A tela inicial deve permitir a seleção entre atendimento Preferencial e Normal.                                                                 |
| RF05 | O sistema deve permitir a digitação do CPF do paciente.                                                                                         |
| RF06 | O sistema deve buscar, via API do SGG, se há agendamento para o CPF informado dentro das agendas configuradas.                                  |
| RF07 | O sistema deve exibir os dados cadastrais do paciente para confirmação.                                                                         |
| RF08 | Havendo agendamento, o sistema deve atualizar seu status de "Agendado" para "Aguardando" via API.                                               |
| RF09 | Não havendo agendamento, o sistema deve criar um novo agendamento via API, na agenda de encaixe configurada, vinculado ao cadastro do paciente. |
| RF10 | Caso o paciente não seja encontrado no SGG, o sistema deve exibir mensagem de erro orientando o direcionamento à recepção.                      |
| RF11 | Após cada atendimento, a tela deve retornar automaticamente ao estado inicial.                                                                  |

## 5. Requisitos Não-Funcionais

-   **Disponibilidade:** o tablet deve operar em modo kiosk/fullscreen
    continuamente durante o horário de atendimento, com recuperação
    automática em caso de queda de rede.

-   **Resiliência à API do SGG:** se a API estiver indisponível, o
    sistema deve exibir mensagem clara e tentar novamente, sem travar a
    interface.

-   **Segurança:** comunicação com a API do SGG via HTTPS;
    credenciais/tokens de acesso armazenados de forma segura (variáveis
    de ambiente/secret manager), nunca expostos no front-end do tablet.

-   **Privacidade:** exibir apenas os dados cadastrais mínimos
    necessários para confirmação (evitar exposição de dados sensíveis na
    tela pública).

-   **Usabilidade:** interface simples, com fontes grandes e poucos
    toques, pensada para uso por pacientes de qualquer faixa etária.

-   **Desempenho:** resposta da busca por CPF em poucos segundos.

-   **Auditabilidade:** registro (log) de cada operação realizada
    (busca, atualização de status, criação de agendamento, erros) para
    rastreabilidade.

## 6. Stack Tecnológica Sugerida

| Camada                       | Tecnologia sugerida                                                | Observação                                                                                        |
|------------------------------|--------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| Front-end (tablet/kiosk)     | React (ou Vue) + Tailwind, empacotado como PWA em modo fullscreen  | Roda no navegador do tablet em modo kiosk; fácil de atualizar remotamente                         |
| Back-end / API intermediária | Python (FastAPI/Django) ou Node.js (Express/NestJS)                | Camada própria entre o totem e a API do SGG — centraliza autenticação, regras de negócio e logs   |
| Banco de dados               | PostgreSQL                                                         | Armazena configuração de agendas monitoradas, mapeamento de fallback e logs de operação           |
| Integração                   | Cliente HTTP para consumo da API do SGG (REST)                     | Depende da documentação da API do SGG (autenticação, endpoints de agenda, paciente e agendamento) |
| Painel administrativo        | Mesma stack do front-end, rota protegida por login                 | Onde o administrador seleciona agendas e configura fallback                                       |
| Infraestrutura               | Servidor interno da empresa ou VPS simples (ex.: 1 vCPU / 2GB RAM) | Baixo custo, tráfego previsível                                                                   |

Dado que a stack (Python/SQL/Django/PostgreSQL) já é dominada
internamente, a construção pode aproveitar ferramentas já usadas em
outros projetos da equipe.

## 7. Escopo do MVP

O MVP entrega o fluxo essencial de ponta a ponta, com configuração
administrativa mínima viável:

1.  **Autenticação com a API do SGG** e leitura de agendas/locais de
    atendimento.

2.  **Painel administrativo simples:** lista de agendas do SGG com
    checkbox para "monitorar" + seleção de agenda de encaixe (dropdown)
    por agenda monitorada.

3.  **Tela do totem:** seleção Preferencial/Normal → campo de CPF →
    busca → confirmação de dados → atualização de status ou criação de
    agendamento → tela de sucesso → retorno automático.

4.  **Tratamento do caso "paciente não encontrado no SGG"** com mensagem
    de direcionamento à recepção.

5.  **Log básico** das operações (busca, sucesso, erro) para auditoria.

Ficam para uma fase 2 (fora do MVP): relatórios de uso/tempo de espera,
múltiplos tablets com configuração centralizada, notificações por
SMS/e-mail, personalização visual (marca da unidade).

## 8. Estimativa de Custo com Desenvolvedor Externo

Estimativa de esforço para o MVP, ajustadr considerando um
**desenvolvedor júnior com apoio de ferramentas de IA generativa** para
codificação (o mesmo perfil/abordagem usado no desenvolvimento interno
deste projeto). O uso de IA reduz o tempo em tarefas de boilerplate,
integração de API e depuração — por isso as horas abaixo já são \~35-40%
menores do que uma estimativa tradicional sem IA.

| Etapa                                                                                                                                   | Horas estimadas |
|-----------------------------------------------------------------------------------------------------------------------------------------|-----------------|
| Levantamento de requisitos e estudo da API do SGG                                                                                       | 6h              |
| Camada de integração com a API do SGG (autenticação, consulta de agendas, busca por CPF, atualização de status, criação de agendamento) | 22h             |
| Painel administrativo (seleção de agendas monitoradas e agenda de encaixe)                                                              | 12h             |
| Interface do tablet (fluxo completo Preferencial/Normal → CPF → confirmação → status)                                                   | 16h             |
| Testes e ajustes                                                                                                                        | 10h             |
| Deploy, documentação e entrega                                                                                                          | 6h              |
| **Total**                                                                                                                               | **\~72h**       |

**Faixas de mercado para um desenvolvedor externo com o mesmo perfil
(júnior + IA):**

-   Freelancer júnior com apoio de IA: R$ 60–90/h → **R$ 4.320 – R$
    6.480**

-   Consultoria/agência (equipe pleno/sênior, modelo tradicional): R$
    150–200/h → **R$ 10.800 – R$ 14.400**

*(Valores de referência de mercado; recomenda-se validar com 2–3
cotações reais antes de citar um número fechado à diretoria.)*

### Economia estimada ao ser desenvolvido internamente

Como o sistema é construído por você, como parte das suas atividades
como Trainee de TI e usando as mesmas ferramentas de IA que tornariam um
desenvolvedor externo júnior competitivo em prazo, o custo incremental
para a empresa é essencialmente o tempo já remunerado dentro do seu
contrato — sem contratação externa, sem gestão de fornecedor e sem custo
de manutenção terceirizada recorrente.

| Cenário                            | Custo estimado                             |
|------------------------------------|--------------------------------------------|
| Freelancer júnior externo (com IA) | R$ 4.320 – R$ 6.480                        |
| Consultoria/agência externa        | R$ 10.800 – R$ 14.400                      |
| Desenvolvimento interno (você)     | Custo já absorvido pelo salário do trainee |
| **Economia direta estimada**       | **R$ 4.320 – R$ 14.400**                   |

Além da economia direta, há ganhos indiretos relevantes para o argumento
junto à diretoria: redução de tempo de espera e filas na recepção,
redução de erros manuais de atualização de status, e liberação de horas
da equipe de recepção para atendimentos que exigem intervenção humana.
