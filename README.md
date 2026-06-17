# Furima AI

AIによる出品支援と商品レコメンド機能を備えたフリマアプリです。

## 概要

Furima AI は、商品の出品・購入・管理ができるフリマアプリです。

基本的なフリマアプリの機能に加えて、OpenAI APIを利用した以下のAI機能を実装しました。

* 商品情報から説明文を自動生成する機能
* ユーザーが自然文で入力した条件に近い商品を推薦するAIレコメンド機能

出品者にとっては、商品説明文を書く手間を減らせるようにし、購入者にとっては、キーワード検索だけでは探しにくい商品も見つけやすくなるようにすることを目指しました。

## 公開URL

* Frontend: https://furima-ai-frontend.vercel.app
* Backend: https://furima-ai-backend-796764136746.us-central1.run.app

## 主な機能

### ユーザー認証

Firebase Authenticationを使い、メールアドレスとパスワードによる認証を実装しています。

* 新規登録
* ログイン
* ログアウト
* ログイン状態に応じた表示切り替え
* 認証済みユーザーとDB上のユーザー情報の同期

### 商品一覧

出品されている商品をカード形式で一覧表示します。

表示している情報は以下です。

* 商品名
* 価格
* 商品画像
* 商品説明
* カテゴリ
* 商品状態
* 販売状況

商品画像のサイズが異なる場合でもカードのレイアウトが崩れにくいように、画像表示部分の高さを固定しています。

### 商品検索・フィルタ

商品一覧画面では、商品を探しやすくするために検索・フィルタ機能を実装しています。

* キーワード検索
* カテゴリフィルタ
* 販売状況フィルタ
* 検索結果件数の表示
* 条件リセット

検索対象は、商品名・説明文・カテゴリ・商品の状態です。

### 商品詳細

商品カードから商品詳細画面に遷移し、商品の詳しい情報を確認できます。

* 商品名
* 価格
* 商品説明
* 出品者
* カテゴリ
* 商品状態
* 販売状況
* 作成日

AIレコメンド画面から商品詳細に遷移した場合でも、前の画面に戻れるようにしています。

### 出品

ログインユーザーは商品を出品できます。

入力項目は以下です。

* 商品名
* 商品説明
* 価格
* 画像URL
* カテゴリ
* 商品状態

出品前には確認画面を表示し、誤って出品してしまうことを防ぐようにしています。

### AI商品説明文生成

OpenAI APIを利用して、商品情報から自然な商品説明文を生成します。

出品時に、商品名・カテゴリ・状態・価格をもとに説明文を生成できるようにしました。
商品説明を一から考える負担を減らし、出品までの手間を少なくすることを目的としています。

### AI商品レコメンド

ユーザーが自然文で欲しい商品の条件を入力すると、出品中の商品から条件に近い商品を推薦します。

例:

* 通学に使えるシンプルなバッグが欲しい
* 一人暮らしに便利な家電が欲しい
* 友達へのプレゼントに良さそうな小物が欲しい

実装では、ユーザーの入力文と商品情報をOpenAIのEmbeddingモデルでベクトル化し、cosine similarityを使って類似度を計算しています。
また、カテゴリや商品名に含まれるキーワードも補助的に利用し、明示された条件に近い商品が上位に来やすいように調整しています。

AIレコメンド画面では、一度入力した質問文や推薦結果がページ遷移後も残るようにしています。

### 購入

ログインユーザーは販売中の商品を購入できます。

* 購入前の確認モーダル表示
* 購入後の商品ステータス変更
* 売り切れ商品の表示
* 自分が出品した商品の購入制限

購入が完了すると、商品ステータスは `sold` に変更されます。

### マイページ

ログインユーザーはマイページで自分の情報や取引状況を確認できます。

* ユーザー情報
* 自分が出品した商品一覧
* 自分が購入した商品一覧
* 商品詳細への遷移

### 商品編集

自分が出品した商品は、出品後でも編集できます。

編集できる項目は以下です。

* 商品名
* 商品説明
* 価格
* 画像URL
* カテゴリ
* 商品状態

商品編集は出品者本人のみ行えるように、バックエンド側でも認可チェックを行っています。

### 出品取り消し

自分が出品した販売中の商品は、出品を取り消すことができます。

取り消し前には確認モーダルを表示し、誤操作を防ぐようにしています。
また、購入済みの商品は削除できないようにしています。

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
```

AI機能では、FastAPI BackendからOpenAI APIを呼び出しています。

```text
FastAPI Backend
  ↓
OpenAI API
```

## 画面構成

* 商品一覧画面
* 商品詳細画面
* 出品画面
* AIレコメンド画面
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
REACT_APP_API_BASE_URL=https://furima-ai-backend-796764136746.us-central1.run.app

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
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

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
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

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

### 自然文で探せるAIレコメンド

欲しい商品のイメージを文章で入力すると、条件に近い商品を推薦するAIレコメンド機能を実装しました。

単純なキーワード一致ではなく、ユーザーの入力文と商品情報をEmbeddingモデルでベクトル化し、意味的な近さをもとに推薦しています。
そのうえで、カテゴリやキーワードによるスコア付けも加えることで、入力内容により合った商品が上位に来るようにしました。

### AIによる出品支援

フリマアプリでは、商品説明文を書くことが出品のハードルになりやすいと考えました。
そこで、商品名・カテゴリ・状態・価格などの情報をもとに、AIが自然な説明文を生成する機能を実装しました。

### 出品後の管理機能

出品後に価格や説明文を変更したいケースを想定し、自分の商品だけを編集できる機能を実装しました。
また、販売中の商品については出品を取り消せるようにし、より実用的な出品管理ができるようにしました。

### フリマアプリらしい検索体験

商品数が増えた場合でも目的の商品を探しやすくするため、キーワード検索、カテゴリフィルタ、販売状況フィルタを実装しました。

AIレコメンドと通常の検索・フィルタを分けることで、目的が明確なときは検索、ざっくり探したいときはAIレコメンド、という使い分けができるようにしています。

### 本番環境へのデプロイ

FrontendをVercel、BackendをCloud Run、DatabaseをCloud SQLに分けてデプロイしました。
開発の途中から本番環境で動作確認できる状態にしておくことで、最後にデプロイで詰まるリスクを減らしました。

### UIの調整

商品カード、商品詳細、出品フォーム、確認モーダル、AIレコメンド画面などを整え、フリマアプリとして自然に使える見た目を意識しました。

画像サイズが異なる商品でもカードレイアウトが崩れないようにし、商品一覧とAIレコメンド結果の見た目も揃えています。

## 今後の展望

* 商品画像複数アップロード機能
* お気に入り機能
* コメント・問い合わせ機能
* 価格帯フィルタ
* 並び替え機能
* AIによるカテゴリ自動推定
* AIによる適正価格提案
* レコメンド精度の改善
* ユーザーごとの閲覧・購入履歴を使ったパーソナライズ
* 取引メッセージ機能
* 商品を削除するのではなく非公開化する機能

## 開発者

* yuyq367
