# Furima AI

AI機能搭載・次世代フリマアプリ

## 概要

Furima AI は、商品の出品・購入・管理ができるフリマアプリです。
通常のフリマ機能に加えて、OpenAI APIを活用した商品説明文の自動生成機能を実装しています。

出品者は、商品名・カテゴリ・状態・価格などを入力することで、AIに自然な商品説明文を生成させることができます。
これにより、出品時に説明文を考える負担を減らし、より簡単に商品を出品できる体験を目指しました。

## 公開URL

* Frontend: https://furima-ai-frontend.vercel.app
* Backend: https://furima-ai-backend-796764136746.us-central1.run.app

## 主な機能

### ユーザー認証

Firebase Authenticationを用いて、メールアドレスとパスワードによる認証を実装しています。

* 新規登録
* ログイン
* ログアウト
* ログイン状態に応じた表示切り替え

### 商品一覧

出品されている商品をカード形式で一覧表示します。

* 商品名
* 価格
* 商品画像
* 商品説明
* カテゴリ
* 商品状態
* 販売状況

を表示します。

### 商品検索・フィルタ

商品一覧画面では、目的の商品を探しやすくするために検索・フィルタ機能を実装しています。

* キーワード検索
* カテゴリフィルタ
* 販売状況フィルタ
* 検索結果件数の表示
* 条件リセット

### 商品詳細

商品カードから詳細画面に遷移し、商品の詳しい情報を確認できます。

* 商品名
* 価格
* 商品説明
* 出品者
* カテゴリ
* 商品状態
* 販売状況
* 作成日

を表示します。

### 出品

ログインユーザーは商品を出品できます。

* 商品名
* 商品説明
* 価格
* 画像URL
* カテゴリ
* 商品状態

を入力して出品できます。

### AI商品説明文生成

OpenAI APIを利用して、商品情報から自然な商品説明文を生成します。
出品者が文章を一から考えなくても、商品の魅力が伝わる説明文を作成できるようにしました。

### 購入

ログインユーザーは販売中の商品を購入できます。

* 購入前の確認モーダル表示
* 購入後の商品ステータス変更
* 売り切れ商品の表示
* 自分が出品した商品の購入制限

### マイページ

ログインユーザーはマイページで自分の情報や取引状況を確認できます。

* ユーザー情報
* 自分が出品した商品一覧
* 自分が購入した商品一覧
* 商品詳細への遷移

### 商品編集

自分が出品した商品は、出品後でも編集できます。

* 商品名
* 商品説明
* 価格
* 画像URL
* カテゴリ
* 商品状態

を変更できます。

### 出品取り消し

自分が出品した販売中の商品は、出品を取り消すことができます。
取り消し前には確認モーダルを表示し、誤操作を防ぐようにしています。

## 使用技術

### Frontend

* React
* React Router
* Firebase Authentication
* CSS
* Vercel

### Backend

* Python
* FastAPI
* SQLAlchemy
* PyMySQL
* Firebase Admin SDK
* OpenAI API
* Cloud Run

### Database

* Cloud SQL
* MySQL 8.0

### Infrastructure

* Vercel
* Google Cloud Run
* Google Cloud SQL
* Google Cloud Build
* Firebase Authentication

## アーキテクチャ

```text
User
↓
Vercel
React Frontend
↓
Cloud Run
FastAPI Backend
↓
Cloud SQL
MySQL Database

FastAPI Backend
↓
OpenAI API
```

## 画面構成

* 商品一覧画面
* 商品詳細画面
* 出品画面
* マイページ
* ログイン画面
* 新規登録画面

## ローカル環境での起動方法

### Frontend

```bash
cd furima-ai-frontend
nvm use 20
npm install
npm start
```

ローカルでは以下のURLで起動します。

```text
http://localhost:3000
```

### Backend

```bash
cd furima-ai-backend
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app
```

ローカルでは以下のURLで起動します。

```text
http://127.0.0.1:8000
```

## 環境変数

### Frontend

ローカル環境では `.env` に以下を設定します。

```env
REACT_APP_API_BASE_URL=http://127.0.0.1:8000

REACT_APP_API_KEY=
REACT_APP_AUTH_DOMAIN=
REACT_APP_PROJECT_ID=
REACT_APP_STORAGE_BUCKET=
REACT_APP_MESSAGING_SENDER_ID=
REACT_APP_APP_ID=
```

Vercelでは以下を設定します。

```env
REACT_APP_API_BASE_URL=Cloud Run のURL

REACT_APP_API_KEY=
REACT_APP_AUTH_DOMAIN=
REACT_APP_PROJECT_ID=
REACT_APP_STORAGE_BUCKET=
REACT_APP_MESSAGING_SENDER_ID=
REACT_APP_APP_ID=

CI=false
```

### Backend

ローカル環境では `.env` に以下を設定します。

```env
DB_HOST=
DB_PORT=3306
DB_NAME=furima_ai
DB_USER=
DB_PASSWORD=

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

FIREBASE_PROJECT_ID=
```

Cloud Runでは以下を環境変数として設定します。

```env
DB_NAME=furima_ai
DB_USER=
DB_PASSWORD=
INSTANCE_CONNECTION_NAME=

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

FIREBASE_PROJECT_ID=
```

## デプロイ

### Frontend

FrontendはVercelにデプロイしています。
GitHubのmainブランチに変更が反映されると、Vercelによって自動的に再デプロイされます。

### Backend

BackendはCloud Runにデプロイしています。
GitHubのmainブランチに変更が反映されると、Cloud BuildによってDockerイメージがビルドされ、Cloud Runに自動的に再デプロイされます。

## 工夫した点

### AIによる出品支援

フリマアプリでは、商品説明文を書くことが出品のハードルになりやすいと考えました。
そこで、商品名・カテゴリ・状態・価格などの情報をもとに、AIが自然な説明文を生成する機能を実装しました。

### 出品後の管理機能

出品後に価格や説明文を変更したいケースを想定し、自分の商品だけを編集できる機能を実装しました。
また、販売中の商品については出品を取り消せるようにし、より実用的な出品管理ができるようにしました。

### フリマアプリらしい検索体験

商品数が増えた場合でも目的の商品を探しやすくするため、キーワード検索、カテゴリフィルタ、販売状況フィルタを実装しました。

### 本番環境へのデプロイ

FrontendをVercel、BackendをCloud Run、DatabaseをCloud SQLに分けてデプロイし、実際にインターネット上で利用できる構成にしました。

### UIの調整

商品カード、商品詳細、出品フォーム、確認モーダルなどを整え、フリマアプリとして自然に使える見た目を意識しました。
画像サイズが異なる商品でもカードレイアウトが崩れないように調整しています。

## 今後の展望

* 商品画像アップロード機能
* 商品削除ではなく非公開化する機能
* お気に入り機能
* コメント・問い合わせ機能
* 価格帯フィルタ
* 並び替え機能
* AIによるカテゴリ自動推定
* AIによる適正価格提案
* レコメンド機能
* 取引メッセージ機能

## 開発者

* yuyq367
