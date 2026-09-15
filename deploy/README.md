# EC2 ga deploy

Bitta domen, bitta EC2:

```text
Internet → Nginx :443
             ├─ /      → 127.0.0.1:3000   PM2, next start
             ├─ /api/  → 127.0.0.1:8000   systemd, uvicorn
             └─ (rasmlar S3 dan, to'g'ridan-to'g'ri brauzerga)
PostgreSQL faqat 127.0.0.1:5432
```

Qarorlar:

- `next build` **serverda emas**, GitHub Actions da. Serverga faqat tayyor
  `.next` artefakti tushadi.
- Rasmlar productionda **doim S3** dan (`S3_MODE=production`). `S3_MODE=local`
  faqat dasturchining mashinasi uchun.
- EC2 da AWS kaliti saqlanmaydi. S3 ga kirish **instance role** orqali.
- Region: `ap-northeast-1` (Tokyo).

Domen: `cowork.jdu.uz` yoki `portfolio.cowork.jdu.uz`. Aniq bo'lgach uchta
joyda bir xil qilinadi:

| Joy | Qiymat |
|---|---|
| GitHub `frontend` repo → Variables → `NEXT_PUBLIC_BASE_API_URL` | `https://DOMEN/api/v1/` |
| `backend/.env` → `CORS_ORIGIN` | `https://DOMEN` |
| Nginx `server_name` va `certbot -d` | `DOMEN` |

Repolar (branch `main`):

- https://github.com/jdu-coworking-workspace/kanri_backend.git
- https://github.com/jdu-coworking-workspace/kanri_frontend.git

Deploy fayllari faqat shu papkada. Istisno: PM2 configi frontend repoda,
chunki u ilova papkasida turishi kerak.

| Fayl | Serverdagi joyi |
|---|---|
| `backend/deploy/kanri-api.service` | `/etc/systemd/system/kanri-api.service` |
| `backend/deploy/nginx/kanri.conf` | `/etc/nginx/sites-available/kanri` |
| `backend/deploy/kanri-deploy-frontend.sh` | `/usr/local/bin/kanri-deploy-frontend.sh` |
| `frontend/ecosystem.config.js` | Artefakt bilan keladi, ko'chirilmaydi |

---

# A qism — AWS konsolda (IAM user sifatida)

Tartib muhim: bucket va role instance dan **oldin** yaratiladi, chunki role ni
instance ga ishga tushirish paytida ulash osonroq.

## A1. IAM user ruxsatlari

Konsolga IAM user bilan kirasiz. Bu userga kerak bo'ladi:

- EC2: `RunInstances`, `CreateKeyPair`, `CreateSecurityGroup`,
  `AuthorizeSecurityGroupIngress`, `AllocateAddress`, `AssociateAddress`,
  `Describe*`
- IAM: `CreateRole`, `PutRolePolicy`, `AttachRolePolicy`,
  `CreateInstanceProfile`, `AddRoleToInstanceProfile`, `PassRole`
- S3: `CreateBucket`, `PutBucketPolicy`, `PutObject`

`AdministratorAccess` bo'lsa ham bo'ladi. `iam:PassRole` bo'lmasa instance ga
role ulay olmaysiz — eng ko'p uchraydigan to'siq shu.

Yuqori o'ng burchakda region **Asia Pacific (Tokyo) ap-northeast-1** turganini
tekshiring. Barcha resurslar shu regionda bo'lishi kerak.

## A2. S3 bucket (rasmlar + deploy artefakti)

S3 → Create bucket.

- Name: `kanri-cowork-media` (global unikal bo'lishi kerak, band bo'lsa
  oxiriga son qo'shing va keyin hamma joyda shu nomni ishlatasiz)
- Region: `ap-northeast-1`
- Object Ownership: **ACLs disabled** (default)
- Block Public Access: **"Block all public access" belgisini olib tashlang**

Nega ochiq: backend avatar uchun doimiy URL qaytaradi
(`https://bucket.s3.region.amazonaws.com/avatars/...`) va brauzer uni to'g'ridan
to'g'ri oladi. Ochiq o'qish faqat `avatars/` prefiksiga beriladi.

Bucket → Permissions → Bucket policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadAvatars",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::kanri-cowork-media/avatars/*"
    }
  ]
}
```

`deploy/` prefiksi shu policy ga kirmaydi, ya'ni artefaktlar yopiq qoladi.

## A3. EC2 uchun IAM role

IAM → Roles → Create role.

- Trusted entity: AWS service → **EC2**
- Permissions: `AmazonSSMManagedInstanceCore` (GitHub Actions serverga
  buyruq yuborishi uchun)
- Name: `kanri-ec2-role`

Yaratilgach role ichida Add permissions → Create inline policy → JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::kanri-cowork-media/avatars/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::kanri-cowork-media/deploy/*"
    }
  ]
}
```

Nomi: `kanri-s3-access`. Shu role bo'lgani uchun `.env` da AWS kaliti
kerak emas.

## A4. Key pair

EC2 → Key pairs → Create key pair.

- Name: `kanri`
- Type: RSA, format `.pem`

Yuklab olingan faylni saqlang:

```bash
mv ~/Downloads/kanri.pem ~/.ssh/kanri.pem
chmod 400 ~/.ssh/kanri.pem
```

Bu faylni qaytadan yuklab olish imkoni yo'q.

## A5. Security group

EC2 → Security groups → Create security group. Name: `kanri-web`.

Inbound rules:

| Type | Port | Source |
|---|---|---|
| SSH | 22 | My IP |
| HTTP | 80 | `0.0.0.0/0` |
| HTTPS | 443 | `0.0.0.0/0` |

3000, 8000, 5432 ochilmaydi. GitHub Actions SSH ishlatmaydi (SSM orqali
boradi), shuning uchun 22 ni internetga ochish kerak emas.

## A6. Instance

EC2 → Launch instance.

- Name: `kanri-prod`
- AMI: **Ubuntu Server 24.04 LTS**, 64-bit **x86**
- Type: **t3.small**
- Key pair: `kanri`
- Network → Security group: mavjud `kanri-web` ni tanlang
- Storage: 30 GB gp3
- Advanced details → **IAM instance profile: `kanri-ec2-role`**

`t3.micro` ham yetadi, chunki build serverda emas. Lekin 1 GB RAM da
Postgres bilan birga tig'iz bo'ladi.

Arxitektura x86 bo'lishi shart. Graviton (arm64) olsangiz `sharp` va boshqa
native paketlar mos kelmaydi.

## A7. Elastic IP

EC2 → Elastic IPs → Allocate → Associate → `kanri-prod`.

Bu IP DNS uchun ishlatiladi. Oddiy public IP restartda o'zgarib ketadi.

## A8. Instance ID ni yozib qo'ying

Instance sahifasidan `i-0abc...` ni ko'chirib oling. GitHub Actions uchun
kerak bo'ladi.

---

# B qism — Serverni sozlash

```bash
ssh -i ~/.ssh/kanri.pem ubuntu@ELASTIC_IP
```

## B1. Paketlar

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git nginx postgresql postgresql-contrib \
  python3-venv python3-pip curl ufw rsync unzip

curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2
sudo apt install -y certbot python3-certbot-nginx
```

AWS CLI (deploy skripti uchun):

```bash
curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscli.zip
unzip -q /tmp/awscli.zip -d /tmp && sudo /tmp/aws/install
aws sts get-caller-identity
```

Oxirgi buyruq `kanri-ec2-role` ni ko'rsatishi kerak. Xato bersa instance ga
role ulanmagan.

SSM agent (Ubuntu AMI da odatda bor):

```bash
sudo snap list amazon-ssm-agent || sudo snap install amazon-ssm-agent --classic
sudo snap start amazon-ssm-agent 2>/dev/null || true
```

Konsolda Systems Manager → Fleet Manager da instance ko'rinishi kerak.

## B2. Firewall va foydalanuvchi

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable

sudo adduser --disabled-password --gecos "" kanri
sudo mkdir -p /var/www/kanri
sudo chown kanri:kanri /var/www/kanri
```

## B3. PostgreSQL

```bash
sudo -u postgres psql
```

```sql
CREATE USER kanri WITH PASSWORD 'kuchli-parol';
CREATE DATABASE cowork_db OWNER kanri;
\q
```

## B4. Backend

```bash
sudo -u kanri -H bash
cd /var/www/kanri
git clone -b main https://github.com/jdu-coworking-workspace/kanri_backend.git backend
git clone -b main https://github.com/jdu-coworking-workspace/kanri_frontend.git frontend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
openssl rand -hex 32
nano .env
```

`.env` da to'ldiriladi: `DATABASE_URL` paroli, `JWT_SECRET_KEY`,
`CORS_ORIGIN=https://DOMEN`, `AWS_S3_BUCKET_NAME`. `AWS_ACCESS_KEY_ID` va
`AWS_SECRET_ACCESS_KEY` **bo'sh qoladi**.

```bash
alembic upgrade head
python src/database/seed_users.py
exit
```

```bash
sudo cp /var/www/kanri/backend/deploy/kanri-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now kanri-api
curl -sS http://127.0.0.1:8000/
```

`{"message":"Cowork API is running"}` chiqishi kerak.

## B5. Frontend deploy skripti

```bash
sudo cp /var/www/kanri/backend/deploy/kanri-deploy-frontend.sh /usr/local/bin/
sudo chmod 755 /usr/local/bin/kanri-deploy-frontend.sh
echo 'DEPLOY_BUCKET=kanri-cowork-media' | sudo tee /etc/kanri-deploy.env
```

## B6. PM2 ni autostartga qo'yish

```bash
sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u kanri --hp /home/kanri
```

Chiqqan `sudo` qatorini bajaring. PM2 ilova birinchi deploydan keyin
qo'shiladi.

## B7. Nginx

```bash
sudo cp /var/www/kanri/backend/deploy/nginx/kanri.conf /etc/nginx/sites-available/kanri
sudo nano /etc/nginx/sites-available/kanri     # server_name
sudo ln -sf /etc/nginx/sites-available/kanri /etc/nginx/sites-enabled/kanri
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

---

# C qism — DNS va HTTPS

Domen panelida A yozuv: `cowork` (yoki `portfolio.cowork`) → Elastic IP.

```bash
dig +short cowork.jdu.uz
```

Elastic IP qaytargach:

```bash
sudo certbot --nginx -d cowork.jdu.uz
```

Certbot 443 blokini va HTTP→HTTPS redirectni o'zi qo'shadi. `/api/` va `/`
location lari joyida qolishi kerak.

HTTPS ishlamaguncha login ishlamaydi, chunki cookie `Secure`. Shuning uchun
tartib: Nginx → DNS → certbot → keyin sinash.

---

# D qism — Frontend ni birinchi marta chiqarish

Avtomatlashtirishdan oldin qo'lda bir marta o'tkazing.

Lokal mashinada, frontend repo ichida:

```bash
NEXT_PUBLIC_BASE_API_URL=https://cowork.jdu.uz/api/v1/ npm run build
tar -czf frontend.tar.gz .next public package.json package-lock.json \
  next.config.js ecosystem.config.js
aws s3 cp frontend.tar.gz s3://kanri-cowork-media/deploy/frontend-manual.tar.gz
```

Serverda:

```bash
sudo /usr/local/bin/kanri-deploy-frontend.sh deploy/frontend-manual.tar.gz
sudo -u kanri pm2 save
```

Brauzerda `https://cowork.jdu.uz` ochilib, login ishlashi kerak.

---

# E qism — GitHub Actions

Qo'lda deploy ishlaganidan keyin ulanadi.

## E1. GitHub OIDC uchun AWS role

IAM → Identity providers → Add provider → **OpenID Connect**:

- Provider URL: `https://token.actions.githubusercontent.com`
- Audience: `sts.amazonaws.com`

IAM → Roles → Create role → Web identity → shu provider. Trust policy ni
qo'lda shunday qiling:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:jdu-coworking-workspace/kanri_frontend:*"
        }
      }
    }
  ]
}
```

`sub` shartini tashlab ketmang — aks holda istalgan GitHub repo shu role ni
ola oladi.

Inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::kanri-cowork-media/deploy/*"
    },
    {
      "Effect": "Allow",
      "Action": ["ssm:SendCommand", "ssm:GetCommandInvocation"],
      "Resource": "*"
    }
  ]
}
```

Role nomi: `kanri-github-deploy`.

## E2. GitHub sozlamalari

`kanri_frontend` repo → Settings → Secrets and variables → Actions.

Variables:

| Nom | Qiymat |
|---|---|
| `NEXT_PUBLIC_BASE_API_URL` | `https://cowork.jdu.uz/api/v1/` |
| `AWS_REGION` | `ap-northeast-1` |
| `DEPLOY_BUCKET` | `kanri-cowork-media` |
| `EC2_INSTANCE_ID` | `i-0abc...` |

Secrets:

| Nom | Qiymat |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | `arn:aws:iam::ACCOUNT_ID:role/kanri-github-deploy` |

Workflow fayli frontend repoda: `.github/workflows/deploy.yml`.

Domen o'zgarganda `NEXT_PUBLIC_BASE_API_URL` variable ini yangilab, workflow
ni qaytadan ishga tushirasiz. Serverda hech narsa qilish kerak emas.

---

# F qism — Tekshiruv

| Tekshiruv | Kutilyotgan |
|---|---|
| `ss -lnt` | 3000 va 8000 faqat `127.0.0.1` |
| Tashqaridan `:8000` | ulanmaydi |
| Login | cookie `Secure`, `HttpOnly`, `SameSite=Lax` |
| Avatar yuklash | URL `https://BUCKET.s3.ap-northeast-1.amazonaws.com/avatars/...` |
| Avatar ko'rinishi | Brauzerda 200, 403 emas |

307 redirect sxemasi. `projects` va `users` FastAPI da `/` bilan aniqlangan,
frontend esa slashsiz chaqiradi:

```bash
curl -sI https://cowork.jdu.uz/api/v1/projects | grep -i location
```

`Location` **https://** bo'lishi shart. `http://` chiqsa `--proxy-headers`
ishlamayapti va brauzer so'rovni mixed content deb bloklaydi.

Loglar:

```bash
sudo journalctl -u kanri-api -f
sudo -u kanri pm2 logs kanri-frontend
```

---

# G qism — Ishga tushirishdan oldin

## G1. Seed parollari

`seed_users.py` olti akkauntni `password123` bilan yaratadi. Keraksizlarini
o'chirib, qolganlarining parolini almashtiring.

## G2. HSTS

Certbot HSTS qo'shmaydi. HTTPS ishonchli ishlagach 443 blokiga:

```nginx
add_header Strict-Transport-Security "max-age=31536000" always;
```

Avval sertifikat va redirect to'g'ri ekaniga ishonch hosil qiling — HSTS ni
brauzerdan qaytarib olish qiyin.

## G3. Backup

```bash
sudo -u postgres pg_dump cowork_db | gzip > ~/cowork_$(date +%F).sql.gz
```

Cron ga qo'ying va nusxani S3 ga yuboring. Avatarlar S3 da bo'lgani uchun
ularni alohida saqlash shart emas, lekin bucket uchun versioning yoqish
mumkin.

## G4. `/docs` bu arxitekturada yopiq

Swagger `/docs` da, `/api/` ostida emas. Nginx `/` ni Next.js ga beradi,
shuning uchun 404 qaytadi. Kerak bo'lsa tunnel:

```bash
ssh -i ~/.ssh/kanri.pem -L 8000:127.0.0.1:8000 ubuntu@ELASTIC_IP
# http://127.0.0.1:8000/docs
```

---

# H qism — Keyingi yangilanishlar

Backend (qo'lda):

```bash
sudo -u kanri -H bash -c 'cd /var/www/kanri/backend && git pull && \
  source venv/bin/activate && pip install -r requirements.txt && alembic upgrade head'
sudo systemctl restart kanri-api
```

Frontend: `main` ga push qilinsa GitHub Actions o'zi build qilib chiqaradi.
