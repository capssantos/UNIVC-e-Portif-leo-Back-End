# 🧭 UNIVC — API de Autenticação e Usuários

Serviço de autenticação e controle de usuários com suporte a:

* Pré-cadastro e cadastro completo (step1 e step2)
* Login com JWT
* Renovação de tokens
* Consulta e atualização de perfil

---

url: https://apiunivc.carlosp.dev

---

## ⚙️ Configuração

### 📁 `.env`

```env
ENV=DEV

# Banco de Dados
DBNAME=UNIVC
USER=SEU_USUARIO
PASSWORD=SENHA_AQUI
HOST=painel.carlosp.dev
PORT=5432
PGSSLMODE=prefer

# JWT
JWT_SECRET=troque-por-um-segredo-forte
JWT_ALG=HS256
JWT_ISS=univc-auth
JWT_AUD=univc-api
ACCESS_TTL=900
REFRESH_TTL=2592000
```

---

# 🔐 ROTAS DE AUTENTICAÇÃO

## 1️⃣ **Pré-cadastro**

`POST /auth/register/step1`

Cria o usuário com dados mínimos e já retorna **access_token** e **refresh_token**.

### 🧩 Request Body

```json
{
  "nome": "Carlos Antônio Pereira dos Santos",
  "email": "carlos.pereira@univc.edu.br",
  "password": "SenhaSegura123",
  "contato": "(27) 99999-8888"
}
```

### 📤 Response (201)

```json
{
  "message": "ok",
  "user_id": "b8f4f3e4-9a72-4e7b-b8a6-312d47af22b7",
  "new": true,
  "habilitado": true,
  "validacao": false,
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer"
}
```

---

## 2️⃣ **Completar cadastro**

`POST /auth/register/step2`
Requer autenticação com o token recebido no step1.
Atualiza os dados complementares e marca `new = FALSE`.

### 🔐 Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

### 🧩 Request Body

```json
{
  "curso": "Análise e Desenvolvimento de Sistemas",
  "periodo": "Noturno",
  "ano_inicio": 2024,
  "ano_fim": 2026,
  "data_nascimento": "1990-05-22",
  "contato": "(27) 98888-7777",
  "email": "carlos.pereira@univc.edu.br",
  "imagem": "https://cdn.univc.edu.br/avatars/carlos.png"
}
```

### 📤 Response (200)

```json
{
  "message": "cadastro_complementar_ok",
  "user": {
    "id_usuario": "b8f4f3e4-9a72-4e7b-b8a6-312d47af22b7",
    "nome": "Carlos A. P. dos Santos",
    "curso": "Análise e Desenvolvimento de Sistemas",
    "periodo": "Noturno",
    "ano_inicio": 2024,
    "ano_fim": 2026,
    "data_nascimento": "1990-05-22",
    "contato": "(27) 98888-7777",
    "email": "carlos.pereira@univc.edu.br",
    "imagem": "https://cdn.univc.edu.br/avatars/carlos.png",
    "new": false,
    "habilitado": true,
    "validacao": false
  }
}
```

---

## 🖼️ **Upload de Imagem de Perfil**

`POST /users/me/avatar`
Realiza o **upload da imagem de perfil** do usuário autenticado para o **DigitalOcean Spaces**
e retorna apenas a **URL pública** da imagem.
Essa rota **não altera o banco de dados** — o link deve ser usado posteriormente (por exemplo, no `step2`).

---

### 🔐 Headers

```http
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

---

### 🧩 Campos do FormData

| Campo    | Tipo    | Obrigatório | Descrição                       |
| -------- | ------- | ----------- | ------------------------------- |
| `imagem` | arquivo | ✅           | Arquivo de imagem a ser enviado |

---

### 🧾 Exemplo de Requisição

#### ✅ cURL

```bash
curl -X POST https://apiunivc.carlosp.dev/users/me/avatar \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -F "imagem=@/caminho/para/avatar.png"
```

#### ✅ JavaScript (fetch)

```js
const form = new FormData();
form.append("imagem", fileInput.files[0]);

const res = await fetch("https://apiunivc.carlosp.dev/users/me/avatar", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
  body: form,
});

const data = await res.json();
console.log("URL pública:", data.url);
```

---

### 📤 Response (200)

```json
{
  "message": "upload_ok",
  "url": "https://onicode.nyc3.digitaloceanspaces.com/UNIVC/e-Portifoleo/2025/11/07/1f9a4b8c7d8145f99ab72d9b6e67d0b7.png"
}
```

---

### ⚠️ Possíveis Erros

| Código | Motivo                                    |
| ------ | ----------------------------------------- |
| 400    | `Content-Type` incorreto ou arquivo vazio |
| 400    | Campo `imagem` ausente                    |
| 401    | Token ausente ou inválido                 |
| 500    | Falha no upload para DigitalOcean Spaces  |

---

### 🧱 Fluxo sugerido

```mermaid
sequenceDiagram
    participant U as Usuário
    participant API as UNIVC API
    participant DO as DigitalOcean Spaces

    U->>API: POST /users/me/avatar<br>(imagem)
    API->>DO: upload arquivo
    DO-->>API: URL pública
    API-->>U: { "url": "<link_publico>" }

    Note right of U: Usa o link retornado<br>no step2:<br>"imagem": "<url>"
```

---

## 3️⃣ **Login**

`POST /auth/login`

### 🧩 Request Body

```json
{
  "email": "carlos.pereira@univc.edu.br",
  "password": "SenhaSegura123"
}
```

### 📤 Response (200)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer"
}
```

---

## 4️⃣ **Renovar Tokens**

`POST /auth/refresh`

Gera novos `access_token` e `refresh_token` a partir de um refresh válido.

### 🧩 Request Body

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
}
```

### 📤 Response (200)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer"
}
```

---

## 5️⃣ **Logout / Revogar Token**

`POST /auth/logout`

Revoga o token informado (access ou refresh).

### 🧩 Request Body

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
}
```

### 📤 Response (200)

```json
{ "revoked": true }
```

---

# 👤 ROTAS DE USUÁRIO

## 6️⃣ **Consultar perfil autenticado**

`GET /users/me`

Retorna informações do usuário logado com base no token JWT.

### 🔐 Headers

```
Authorization: Bearer <access_token>
```

### 📤 Response (200)

```json
{
  "user": {
    "id_usuario": "b8f4f3e4-9a72-4e7b-b8a6-312d47af22b7",
    "nome": "Carlos Antônio Pereira dos Santos",
    "email": "carlos.pereira@univc.edu.br",
    "contato": "(27) 99999-8888",
    "curso": "Análise e Desenvolvimento de Sistemas",
    "periodo": "Noturno",
    "ano_inicio": 2024,
    "ano_fim": 2026,
    "data_nascimento": "1990-05-22",
    "imagem": "https://cdn.univc.edu.br/avatars/carlos.png",
    "new": false,
    "habilitado": true,
    "validacao": true
  }
}
```

---

## 7️⃣ **Atualizar perfil autenticado**

`PUT /users/me`

Permite atualizar os dados do usuário logado (exceto senha).

### 🔐 Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

### 🧩 Request Body (exemplo)

```json
{
  "curso": "ADS",
  "periodo": "Noturno",
  "ano_inicio": 2024,
  "ano_fim": 2026,
  "data_nascimento": "1990-05-22",
  "contato": "(27) 99999-7777",
  "imagem": "https://cdn.univc.edu.br/avatars/carlos-novo.png",
  "validacao": true
}
```

### 📤 Response (200)

```json
{
  "message": "ok",
  "user": {
    "id_usuario": "b8f4f3e4-9a72-4e7b-b8a6-312d47af22b7",
    "nome": "Carlos Pereira",
    "curso": "ADS",
    "periodo": "Noturno",
    "ano_inicio": 2024,
    "ano_fim": 2026,
    "data_nascimento": "1990-05-22",
    "contato": "(27) 99999-7777",
    "imagem": "https://cdn.univc.edu.br/avatars/carlos-novo.png",
    "validacao": true,
    "updated_at": "2025-11-07T20:10:03"
  }
}
```

🧩 1️⃣ Criar curso (POST /cursos/)
➡️ Requisição
```json
{
  "nome": "Técnico em Desenvolvimento de Sistemas",
  "descricao": "Curso focado em programação, banco de dados e engenharia de software."
}
```

⬅️ Resposta (201)
```json
{
  "message": "Curso criado com sucesso",
  "curso": {
    "id_curso": "b7b9a7a8-3e21-4a2e-9b31-2ed73ffb6f4a",
    "nome": "Técnico em Desenvolvimento de Sistemas",
    "descricao": "Curso focado em programação, banco de dados e engenharia de software.",
    "habilitado": true
  }
}
```

📋 2️⃣ Listar cursos habilitados (GET /cursos/)
➡️ Requisição

Sem corpo (GET puro)

⬅️ Resposta (200)
```json
[
  {
    "id_curso": "b7b9a7a8-3e21-4a2e-9b31-2ed73ffb6f4a",
    "nome": "Técnico em Desenvolvimento de Sistemas",
    "descricao": "Curso focado em programação, banco de dados e engenharia de software.",
    "habilitado": true,
    "created_at": "2025-11-12T15:00:00"
  },
  {
    "id_curso": "e9f7a123-6cda-4e22-b64e-8c7652e4a9d1",
    "nome": "Redes de Computadores",
    "descricao": "Configuração e manutenção de redes TCP/IP.",
    "habilitado": true,
    "created_at": "2025-11-11T18:00:00"
  }
]
```

🔍 3️⃣ Obter curso por ID (GET /cursos/<id_curso>)
➡️ Requisição

Sem corpo
Exemplo:
GET /cursos/b7b9a7a8-3e21-4a2e-9b31-2ed73ffb6f4a

⬅️ Resposta (200)
```json
{
  "id_curso": "b7b9a7a8-3e21-4a2e-9b31-2ed73ffb6f4a",
  "nome": "Técnico em Desenvolvimento de Sistemas",
  "descricao": "Curso focado em programação, banco de dados e engenharia de software.",
  "habilitado": true,
  "created_at": "2025-11-12T15:00:00",
  "updated_at": null
}
```

✏️ 4️⃣ Atualizar curso (PUT /cursos/<id_curso>)
➡️ Requisição
```json
{
  "nome": "Técnico em Desenvolvimento de Sistemas - Atualizado",
  "descricao": "Inclui novas tecnologias como IA generativa e IoT."
}
```

⬅️ Resposta (200)
```json
{
  "message": "Curso atualizado com sucesso"
}
```

🚫 5️⃣ Desabilitar curso (PUT /cursos/<id_curso>/disable)
➡️ Requisição

Sem corpo

⬅️ Resposta (200)
```json
{
  "message": "Curso desabilitado com sucesso"
}
```

Se o curso já estiver desabilitado:
```json
{
  "message": "Curso já está desabilitado"
}
```

✅ 6️⃣ Reabilitar curso (PUT /cursos/<id_curso>/enable)
➡️ Requisição

Sem corpo
```json
⬅️ Resposta (200)
{
  "message": "Curso habilitado com sucesso"
}
```


Se o curso já estiver habilitado:
```json
{
  "message": "Curso já está habilitado"
}
```

⚠️ 7️⃣ Erros comuns
| Situação                  | Status | Exemplo de resposta                           |
| ------------------------- | ------ | --------------------------------------------- |
| Campo obrigatório ausente | `400`  | `{ "error": "O campo 'nome' é obrigatório" }` |
| Curso inexistente         | `404`  | `{ "error": "Curso não encontrado" }`         |
| Erro interno              | `500`  | `{ "error": "mensagem detalhada" }`           |


---

# ⚠️ Códigos de Erro Comuns

| Código | Motivo                       |
| ------ | ---------------------------- |
| 400    | Campos obrigatórios ausentes |
| 401    | Token ausente ou inválido    |
| 404    | Usuário não encontrado       |
| 409    | E-mail já cadastrado         |
| 500    | Erro interno inesperado      |

---

# 🧩 Ciclo de Autenticação — Fluxo Completo

```mermaid
sequenceDiagram
    participant U as Usuário
    participant API as Flask Auth API
    participant DB as PostgreSQL

    U->>API: POST /auth/register/step1<br>nome, email, contato, senha
    API->>DB: INSERT INTO usuarios
    API-->>U: access_token + refresh_token (new = TRUE)

    U->>API: POST /auth/register/step2<br>(autenticado)
    API->>DB: UPDATE usuarios SET new=FALSE
    API-->>U: Dados complementares

    U->>API: POST /auth/login
    API->>DB: SELECT + valida senha
    API-->>U: Novo par de tokens

    U->>API: POST /auth/refresh<br>refresh_token
    API->>DB: Valida e revoga antigo
    API-->>U: Novo par de tokens

    U->>API: GET /users/me<br>(Bearer access_token)
    API->>DB: SELECT dados do usuário
    API-->>U: Perfil completo
```

---

# 🧱 Tecnologias utilizadas

* **Flask** — API web
* **PostgreSQL** — Banco de dados
* **PyJWT** — Geração e validação de JWTs
* **bcrypt** — Hash de senhas
* **psycopg2** — Conexão com Postgres
* **dotenv** — Variáveis de ambiente

---

Quer que eu formate esse README com emojis e seções de **rotas protegidas vs públicas** (pra usar direto na documentação Swagger ou README do repositório UNIVC)?
