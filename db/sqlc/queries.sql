-- name: GetUser :one
SELECT * FROM users WHERE username = $1;

-- name: ListUsers :many
SELECT * FROM users ORDER BY id;

-- name: AddUser :exec
INSERT INTO users (username, password, super_admin)
VALUES ($1, $2, $3);
