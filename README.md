# HomeFlow

Controle de despesas compartilhadas de um casal. Você lança uma compra (à vista ou parcelada), o sistema divide o valor de cada parcela conforme a regra de divisão vigente, calcula quem deve para quem e gera o Pix para acertar o saldo.

## Como funciona

O fluxo central são as despesas e a divisão entre os dois:

- **Compra** — uma despesa, à vista ou em N parcelas. Sempre tem alguém que pagou (`pago_por`).
- **Parcela** — cada uma das N parcelas da compra, com valor e vencimento.
- **Rateio** — quanto cada pessoa deve naquela parcela. O percentual aplicado é gravado no momento do lançamento (snapshot), então mudar a regra depois não reescreve o passado.
- **Regra de divisão** — o split do casal (ex.: 70/30). É versionada por data de vigência: nunca se edita uma regra, cria-se uma nova com `vigente_desde`. Cada compra usa a regra vigente na data dela.

O saldo é o líquido por par: somam-se os rateios pendentes, abate-se o que um deve do outro e mostra-se a direção certa (quem deve para quem). Quem deve, deve para quem **pagou** a parcela.

### Pix

Geração de Pix estático, sem integração com banco/PSP. O sistema monta o BR Code (copia-e-cola, com CRC16) e o QR Code em PNG a favor da chave Pix do credor — pelo saldo total ou por uma parcela específica. Exige que o credor tenha `chave_pix` cadastrada.

### Recorrentes e lembretes

- **Despesas recorrentes** (aluguel, internet, energia...) geram a compra do mês via comando agendado, de forma idempotente (uma compra por competência).
- **Lembretes** por e-mail dos rateios que vencem nos próximos dias, agrupados por pessoa.

## Stack

- Python + Django 6
- PostgreSQL (SQLite por padrão em desenvolvimento)
- WhiteNoise para estáticos, Gunicorn em produção
- `pix-utils` + `qrcode` para o Pix
- pytest / pytest-django

## Estrutura

```
apps/
  core/           # base compartilhada (TimeStampedModel, dinheiro, datas)
  accounts/       # usuário, casal, membros e regras de divisão
  expenses/       # compras, parcelas, rateios e despesas recorrentes
  settlements/    # cálculo de saldo (quem deve para quem)
  payments/       # geração de Pix (BR Code + QR Code)
  notifications/  # lembretes de vencimento por e-mail
  web/            # views, templates e telas
config/
  settings/       # base.py, dev.py, prod.py
```

A lógica de negócio fica em `services.py` (escrita) e `selectors.py` (leitura) de cada app — as views só orquestram.

## Rodando localmente

Requer Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # ajuste SECRET_KEY e, se quiser, o Postgres
```

Deixe `POSTGRES_HOST` vazio no `.env` para usar SQLite. Em seguida:

```bash
python manage.py migrate
python manage.py seed_casal      # cria o casal inicial com regra 70/30
python manage.py createsuperuser
python manage.py runserver
```

O settings de desenvolvimento (`config.settings.dev`) já é o padrão via `manage.py` e `pytest.ini`.

## Testes

```bash
pytest
```

## Comandos

```bash
# Gera as compras das recorrentes ativas da competência (default: mês atual)
python manage.py gerar_recorrentes [--competencia YYYY-MM]

# Envia lembretes dos vencimentos próximos (default: settings.LEMBRETE_DIAS_ANTECEDENCIA)
python manage.py enviar_lembretes [--dias N]
```

Os dois são idempotentes/seguros para rodar em agendador (cron).

## Variáveis de ambiente

Veja `.env.example`. As principais:

| Variável | Descrição |
| --- | --- |
| `SECRET_KEY` | chave secreta do Django |
| `DEVELOPMENT_ENVIRONMENT` | `True`/`False` |
| `DJANGO_ALLOWED_HOST` / `DJANGO_ALLOWED_HOSTS` | hosts permitidos (dev/prod) |
| `POSTGRES_*` | conexão do banco (vazio = SQLite em dev) |
| `EMAIL_*` | SMTP em produção (console em dev) |
| `LEMBRETE_DIAS_ANTECEDENCIA` | antecedência padrão dos lembretes (dias) |

## Produção

O `Procfile` roda `collectstatic`, `migrate` e sobe o Gunicorn com `config.settings.prod`. Em prod o banco é sempre PostgreSQL, e-mail por SMTP e cookies de sessão/CSRF seguros.

## Licença

MIT — veja [LICENSE](LICENSE).
