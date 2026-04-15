# API 接口说明文档

## 概述

- **后端Base URL**: `http://localhost:8000`
- **前端Base URL**: `http://localhost:8000/api`
- **认证方式**: JWT Bearer Token (Header: `Authorization: Bearer {token}`)

---

## 认证接口 (/auth)

### POST /api/auth/register
- **功能**: 用户注册
- **权限**: 公开
- **前端请求URL**: `POST http://localhost:8000/api/auth/register`
- **请求参数** (JSON):
  ```json
  {
    "nickname": "昵称",
    "password": "密码",
    "gender": "性别（可选）",
    "age": 年龄（可选）,
    "avatar_url": "头像URL（可选）",
    "taste": "口味偏好（可选）",
    "is_halal": 是否清真（可选）,
    "allergens": ["过敏源列表"]（可选）,
    "contact": "联系方式（可选）"
  }
  ```
- **返回**: 账户信息

### POST /api/auth/login
- **功能**: 用户登录
- **权限**: 公开
- **前端请求URL**: `POST http://localhost:8000/api/auth/login`
- **请求参数** (JSON):
  ```json
  {
    "account": "账户",
    "password": "密码"
  }
  ```
- **返回**: JWT令牌、账户信息、管理员级别

### GET /api/auth/check-admin
- **功能**: 检查当前用户是否为管理员
- **权限**: 登录用户
- **前端请求URL**: `GET http://localhost:8000/api/auth/check-admin`
- **返回**:
  ```json
  {
    "is_admin": true,
    "admin_level": 0
  }
  ```
  或
  ```json
  {
    "is_admin": false,
    "admin_level": null
  }
  ```

### POST /api/auth/reset-password
- **功能**: 重置密码
- **权限**: 登录用户
- **前端请求URL**: `POST http://localhost:8000/api/auth/reset-password`
- **请求参数** (JSON):
  ```json
  {
    "old_password": "旧密码",
    "new_password": "新密码"
  }
  ```

### POST /api/auth/user-reset-password
- **功能**: 用户重置密码（通过联系方式验证）
- **权限**: 公开
- **前端请求URL**: `POST http://localhost:8000/api/auth/user-reset-password`
- **请求参数** (JSON):
  ```json
  {
    "account": "账户",
    "new_password": "新密码"
  }
  ```

---

## 用户接口 (/users)

### GET /api/users/me
- **功能**: 获取当前用户信息
- **权限**: 登录用户
- **前端请求URL**: `GET http://localhost:8000/api/users/me`
- **返回说明**:
  - `avatar_url`: 用户头像URL（混合存储模式下会自动解析为实际存在的URL）

### GET /api/users/{account}
- **功能**: 获取指定用户公开信息
- **权限**: 公开
- **前端请求URL**: `GET http://localhost:8000/api/users/{account}`
- **返回说明**:
  - `avatar_url`: 用户头像URL（混合存储模式下会自动解析为实际存在的URL）

### PUT /api/users/me
- **功能**: 更新当前用户信息
- **权限**: 登录用户
- **前端请求URL**: `PUT http://localhost:8000/api/users/me`
- **请求参数** (JSON):
  ```json
  {
    "nickname": "昵称",
    "contact": "联系方式",
    "gender": "性别",
    "age": 年龄,
    "avatar_url": "头像URL",
    "taste": "口味偏好",
    "is_halal": 是否清真,
    "allergens": ["过敏源列表"]
  }
  ```

### PUT /api/users/{account}
- **功能**: 管理员更新用户信息
- **权限**: 管理员
- **前端请求URL**: `PUT http://localhost:8000/api/users/{account}`

### DELETE /api/users/{account}
- **功能**: 管理员删除用户（软删除）
- **权限**: 管理员
- **前端请求URL**: `DELETE http://localhost:8000/api/users/{account}`

### POST /api/users/{account}/freeze
- **功能**: 管理员冻结用户
- **权限**: 管理员
- **前端请求URL**: `POST http://localhost:8000/api/users/{account}/freeze`

### POST /api/users/{account}/unfreeze
- **功能**: 管理员解冻用户
- **权限**: 管理员
- **前端请求URL**: `POST http://localhost:8000/api/users/{account}/unfreeze`

### POST /api/users/me/favorites/{recipe_id}
- **功能**: 收藏食谱
- **权限**: 登录用户
- **前端请求URL**: `POST http://localhost:8000/api/users/me/favorites/{recipe_id}`
- **返回**: 是否收藏成功、最多收藏30条

### DELETE /api/users/me/favorites/{recipe_id}
- **功能**: 取消收藏食谱
- **权限**: 登录用户
- **前端请求URL**: `DELETE http://localhost:8000/api/users/me/favorites/{recipe_id}`

### GET /api/users/me/favorites
- **功能**: 获取用户收藏的食谱列表
- **权限**: 登录用户
- **前端请求URL**: `GET http://localhost:8000/api/users/me/favorites`
- **返回**: 收藏的食谱列表（包含名称、难度、菜系、烹饪方式、收藏时间）

### POST /api/users/me/browse/{recipe_id}
- **功能**: 记录浏览历史
- **权限**: 登录用户
- **前端请求URL**: `POST http://localhost:8000/api/users/me/browse/{recipe_id}`
- **备注**: 最多记录50条浏览历史

---

## 食谱接口 (/recipes)

### GET /api/recipes/
- **功能**: 获取公开的食谱列表
- **权限**: 公开
- **前端请求URL**: `GET http://localhost:8000/api/recipes/`
- **查询参数**:
  - `skip`: 跳过条数
  - `limit`: 返回条数
  - `cuisine`: 菜系筛选
  - `is_halal`: 清真筛选
- **示例**: `GET http://localhost:8000/api/recipes/?skip=0&limit=10&cuisine=川菜`
- **返回说明**:
  - `pictures_url`: 食谱封面图片列表（最多3个，混合存储模式下会自动解析为实际存在的URL）
  - `source`: 来源（"系统"或用户昵称）
  - `source_avatar_url`: 来源头像URL（如果来源不是"系统"或"官方"，会返回创建者的头像）

### GET /api/recipes/all
- **功能**: 获取所有食谱列表
- **权限**: 管理员
- **前端请求URL**: `GET http://localhost:8000/api/recipes/all`
- **返回说明**:
  - `pictures_url`: 食谱封面图片列表
  - `source`: 来源
  - `source_avatar_url`: 来源头像URL

### GET /api/recipes/my
- **功能**: 获取当前用户的食谱列表
- **权限**: 登录用户
- **前端请求URL**: `GET http://localhost:8000/api/recipes/my`
- **返回**: 包括私密的食谱
- **返回说明**:
  - `pictures_url`: 食谱封面图片列表
  - `source`: 来源
  - `source_avatar_url`: 来源头像URL

### GET /api/recipes/pending
- **功能**: 获取待审核的食谱列表
- **权限**: 管理员
- **前端请求URL**: `GET http://localhost:8000/api/recipes/pending`
- **返回说明**:
  - `pictures_url`: 食谱封面图片列表
  - `source`: 来源
  - `source_avatar_url`: 来源头像URL

### GET /api/recipes/{recipe_id}
- **功能**: 获取单个食谱
- **权限**: 公开
- **前端请求URL**: `GET http://localhost:8000/api/recipes/{recipe_id}`
- **返回说明**:
  - `pictures_url`: 食谱封面图片列表（最多3个）
  - `source`: 来源（"系统"或用户昵称）
  - `source_avatar_url`: 来源头像URL（如果来源不是"系统"或"官方"，会返回创建者的头像）

### POST /api/recipes/
- **功能**: 创建食谱（管理员创建，系统来源）
- **权限**: 管理员
- **前端请求URL**: `POST http://localhost:8000/api/recipes/`
- **请求参数** (JSON):
  ```json
  {
    "name": "菜品名称",
    "materials": [{"材料名": "材料1", "重量": "100g"}],
    "seasonings": [{"调料名": "盐", "用量": "适量"}],
    "cuisine": "川菜",
    "difficulty": 5,
    "steps": [{"时刻": "1", "操作": "准备食材"}],
    "carbohydrate": 10.5,
    "protein": 20.3,
    "fat": 5.6,
    "vitamins": ["维生素A"],
    "minerals": ["钙"],
    "is_halal": false,
    "allergens": ["虾"],
    "method": "炒",
    "pictures_url": ["封面图1URL", "封面图2URL", "封面图3URL"]
  }
  ```
- **备注**:
  - `pictures_url` 最多支持3个URL，超过3个会自动截断

### POST /api/recipes/my
- **功能**: 用户创建自己的食谱
- **权限**: 登录用户
- **前端请求URL**: `POST http://localhost:8000/api/recipes/my`
- **备注**: 不需要等待15天，默认私密

### POST /api/recipes/share
- **功能**: 用户分享食谱
- **权限**: 登录用户（需注册满15天）
- **前端请求URL**: `POST http://localhost:8000/api/recipes/share`
- **备注**: 分享后需要审核，默认不公开

### PUT /api/recipes/my/{recipe_id}
- **功能**: 更新用户自己的食谱
- **权限**: 登录用户（仅自己的食谱）
- **前端请求URL**: `PUT http://localhost:8000/api/recipes/my/{recipe_id}`
- **备注**: 不能修改系统食谱

### PUT /api/recipes/my/{recipe_id}/share
- **功能**: 分享用户自己的食谱（提交审核）
- **权限**: 登录用户（需注册满15天，仅自己的食谱）
- **前端请求URL**: `PUT http://localhost:8000/api/recipes/my/{recipe_id}/share`
- **备注**: 分享后需要审核

### DELETE /api/recipes/my/{recipe_id}
- **功能**: 删除用户自己的食谱（软删除）
- **权限**: 登录用户（仅自己的食谱）
- **前端请求URL**: `DELETE http://localhost:8000/api/recipes/my/{recipe_id}`
- **备注**: 不能删除系统食谱

### PUT /api/recipes/{recipe_id}/visibility
- **功能**: 切换食谱公开/私密状态
- **权限**: 登录用户（仅自己的食谱）
- **前端请求URL**: `PUT http://localhost:8000/api/recipes/{recipe_id}/visibility`
- **请求参数** (JSON):
  ```json
  {
    "status": "private" // 或 "public"
  }
  ```

### POST /api/recipes/{recipe_id}/approve
- **功能**: 审核通过食谱
- **权限**: 管理员
- **前端请求URL**: `POST http://localhost:8000/api/recipes/{recipe_id}/approve`

### POST /api/recipes/{recipe_id}/reject
- **功能**: 审核拒绝食谱
- **权限**: 管理员
- **前端请求URL**: `POST http://localhost:8000/api/recipes/{recipe_id}/reject`

### PUT /api/recipes/{recipe_id}
- **功能**: 更新食谱
- **权限**: 管理员
- **前端请求URL**: `PUT http://localhost:8000/api/recipes/{recipe_id}`

### DELETE /api/recipes/{recipe_id}
- **功能**: 删除食谱（软删除）
- **权限**: 管理员
- **前端请求URL**: `DELETE http://localhost:8000/api/recipes/{recipe_id}`

---

## 食谱搜索接口 (/recipes-search)

### GET /api/recipes-search/by-ingredient
- **功能**: 通过食材ID搜索食谱
- **权限**: 公开
- **前端请求URL**: `GET http://localhost:8000/api/recipes-search/by-ingredient?ingredient_id=1&skip=0&limit=20`
- **查询参数**:
  - `ingredient_id`: 食材ID（必填）
  - `skip`: 跳过条数
  - `limit`: 返回条数（默认20）
- **返回**: 使用该食材的食谱列表，按匹配度排序（精确匹配优先）

---

## 食材接口 (/ingredients)

### GET /api/ingredients/
- **功能**: 获取食材列表
- **权限**: 公开
- **前端请求URL**: `GET http://localhost:8000/api/ingredients/`
- **查询参数**:
  - `skip`: 跳过条数
  - `limit`: 返回条数
  - `category`: 分类筛选
- **返回说明**:
  - `picture_url`: 食材封面图片URL（混合存储模式下会自动解析为实际存在的URL）

### GET /api/ingredients/{ingredient_id}
- **功能**: 获取单个食材
- **权限**: 公开
- **前端请求URL**: `GET http://localhost:8000/api/ingredients/{ingredient_id}`
- **返回说明**:
  - `picture_url`: 食材封面图片URL（混合存储模式下会自动解析为实际存在的URL）

### POST /api/ingredients/
- **功能**: 创建食材
- **权限**: 管理员
- **前端请求URL**: `POST http://localhost:8000/api/ingredients/`
- **请求参数** (JSON):
  ```json
  {
    "name": ["食材名称"],
    "carbohydrate": 碳水含量,
    "protein": 蛋白质含量,
    "fat": 脂肪含量,
    "vitamins": ["维生素列表"],
    "minerals": ["矿物质列表"],
    "category": "食材种类",
    "is_halal": false,
    "is_allergen": false,
    "picture_url": "封面图片URL（可选）"
  }
  ```

### PUT /api/ingredients/{ingredient_id}
- **功能**: 更新食材
- **权限**: 管理员
- **前端请求URL**: `PUT http://localhost:8000/api/ingredients/{ingredient_id}`

### DELETE /api/ingredients/{ingredient_id}
- **功能**: 删除食材（软删除）
- **权限**: 管理员
- **前端请求URL**: `DELETE http://localhost:8000/api/ingredients/{ingredient_id}`

---

## 文件上传接口 (/upload)

### GET /api/upload/test
- **功能**: 测试存储服务配置
- **权限**: 公开
- **前端请求URL**: `GET http://localhost:8000/api/upload/test`
- **返回**:
  ```json
  {
    "storage_type": "local",
    "cloud_configured": false,
    "local_upload_dir": "uploads",
    "status": "ok"
  }
  ```

### POST /api/upload/image
- **功能**: 上传图片文件
- **权限**: 登录用户
- **前端请求URL**: `POST http://localhost:8000/api/upload/image`
- **请求参数** (Form-Data):
  - `file`: 图片文件（必填，支持 jpeg/png/gif/webp/bmp，最大5MB）
- **返回**:
  ```json
  {
    "url": "图片URL",
    "filename": "原始文件名",
    "size": 文件大小,
    "content_type": "image/jpeg"
  }
  ```

### POST /api/upload/avatar
- **功能**: 上传用户头像
- **权限**: 登录用户
- **前端请求URL**: `POST http://localhost:8000/api/upload/avatar`
- **请求参数** (Form-Data):
  - `file`: 图片文件（必填，支持 jpeg/png/gif/webp/bmp，最大5MB）
- **返回**: 同 `POST /api/upload/image`

### POST /api/upload/cover
- **功能**: 上传封面图片
- **权限**: 登录用户
- **前端请求URL**: `POST http://localhost:8000/api/upload/cover`
- **请求参数** (Form-Data):
  - `file`: 图片文件（必填，支持 jpeg/png/gif/webp/bmp，最大5MB）
- **返回**: 同 `POST /api/upload/image`
- **备注**: 可用于食材封面或食谱封面

---

## 管理员接口 (/admins)

### GET /api/admins/
- **功能**: 获取管理员列表
- **权限**: 0级管理员
- **前端请求URL**: `GET http://localhost:8000/api/admins/`
- **返回**: 只返回1级管理员（不包含0级）

### GET /api/admins/me
- **功能**: 获取当前管理员信息
- **权限**: 管理员
- **前端请求URL**: `GET http://localhost:8000/api/admins/me`

### GET /api/admins/users
- **功能**: 获取用户列表
- **权限**: 管理员
- **前端请求URL**: `GET http://localhost:8000/api/admins/users`

### GET /api/admins/{account}
- **功能**: 获取管理员信息
- **权限**: 管理员
- **前端请求URL**: `GET http://localhost:8000/api/admins/{account}`

### POST /api/admins/ctadmin
- **功能**: 创建1级管理员
- **权限**: 0级管理员
- **前端请求URL**: `POST http://localhost:8000/api/admins/ctadmin`
- **请求参数** (JSON):
  ```json
  {
    "nickname": "管理员昵称",
    "password": "登录密码",
    "permission_duration_days": 权限持续天数（默认30天）
  }
  ```

### PUT /api/admins/{account}
- **功能**: 更新管理员信息
- **权限**: 0级管理员
- **前端请求URL**: `PUT http://localhost:8000/api/admins/{account}`

### DELETE /api/admins/{account}
- **功能**: 删除管理员
- **权限**: 0级管理员
- **前端请求URL**: `DELETE http://localhost:8000/api/admins/{account}`
- **备注**: 不能删除0级管理员

### POST /api/admins/reset-password
- **功能**: 重置管理员密码
- **权限**: 0级管理员
- **前端请求URL**: `POST http://localhost:8000/api/admins/reset-password`

---

## 存储配置说明

### 配置项（.env 文件）

```properties
# 存储类型：cloud(云存储) / local(本地存储) / mixed(混合存储)
STORAGE_TYPE=local

# 腾讯云COS配置（云存储或混合存储时需要配置）
COS_SECRET_ID=your-secret-id
COS_SECRET_KEY=your-secret-key
COS_BUCKET=your-bucket-name
COS_REGION=ap-guangzhou
# 云存储URL过期时间(秒)，默认3600秒
COS_URL_EXPIRE_SECONDS=3600

# 本地存储配置
LOCAL_UPLOAD_DIR=uploads
LOCAL_BASE_URL=/uploads
```

### 存储类型说明

| 类型 | 说明 |
|------|------|
| `local` | 本地文件系统存储，文件保存在 `uploads` 目录 |
| `cloud` | 腾讯云COS存储，需要配置COS_SECRET_ID、COS_SECRET_KEY、COS_BUCKET、COS_REGION |
| `mixed` | 混合存储，优先上传到云存储，失败则使用本地存储；查找时优先查云，云上没有则查本地 |

### 混合存储查找逻辑

当使用混合存储模式时，获取用户头像、食材封面、食谱封面等图片时：
1. 优先在云存储中查找图片
2. 如果云存储中没有，则在本地存储中查找
3. 返回实际存在的图片URL

---

## 权限说明

### 管理员等级
- **0级管理员**: 超级管理员，拥有所有权限
- **1级管理员**: 普通管理员，权限有限

### 权限检查机制
- 非管理员调用管理员接口时，提示"您没有该权限"
- 失败3次后自动冻结账户
- 管理员权限过期后无法使用管理员功能

### 用户注册时间限制
- 用户注册满15天后才能分享食谱
- 用户可以随时创建自己的食谱（默认私密）

---

## 前端代码调用示例

```typescript
import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api'
})

// 登录
const res = await api.post('/auth/login', { account: 'xxx', password: 'xxx' })

// 获取食谱列表
const res = await api.get('/recipes/', { params: { skip: 0, limit: 10 } })

// 获取用户信息（需要认证）
api.defaults.headers.common['Authorization'] = `Bearer ${token}`
const res = await api.get('/users/me')
```