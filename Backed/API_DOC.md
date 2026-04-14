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
- **返回**: 当前用户的完整信息

### GET /api/users/{account}
- **功能**: 获取指定用户公开信息
- **权限**: 公开
- **前端请求URL**: `GET http://localhost:8000/api/users/{account}`
- **返回**: 用户公开信息

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

### GET /api/recipes/all
- **功能**: 获取所有食谱列表
- **权限**: 管理员
- **前端请求URL**: `GET http://localhost:8000/api/recipes/all`

### GET /api/recipes/my
- **功能**: 获取当前用户的食谱列表
- **权限**: 登录用户
- **前端请求URL**: `GET http://localhost:8000/api/recipes/my`
- **返回**: 包括私密的食谱

### GET /api/recipes/pending
- **功能**: 获取待审核的食谱列表
- **权限**: 管理员
- **前端请求URL**: `GET http://localhost:8000/api/recipes/pending`

### GET /api/recipes/{recipe_id}
- **功能**: 获取单个食谱
- **权限**: 公开
- **前端请求URL**: `GET http://localhost:8000/api/recipes/{recipe_id}`

### POST /api/recipes/
- **功能**: 创建食谱（管理员创建，系统来源）
- **权限**: 管理员
- **前端请求URL**: `POST http://localhost:8000/api/recipes/`

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

### GET /api/ingredients/{ingredient_id}
- **功能**: 获取单个食材
- **权限**: 公开
- **前端请求URL**: `GET http://localhost:8000/api/ingredients/{ingredient_id}`

### POST /api/ingredients/
- **功能**: 创建食材
- **权限**: 管理员
- **前端请求URL**: `POST http://localhost:8000/api/ingredients/`

### PUT /api/ingredients/{ingredient_id}
- **功能**: 更新食材
- **权限**: 管理员
- **前端请求URL**: `PUT http://localhost:8000/api/ingredients/{ingredient_id}`

### DELETE /api/ingredients/{ingredient_id}
- **功能**: 删除食材（软删除）
- **权限**: 管理员
- **前端请求URL**: `DELETE http://localhost:8000/api/ingredients/{ingredient_id}`

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