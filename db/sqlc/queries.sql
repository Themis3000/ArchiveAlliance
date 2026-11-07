-- name: GetUser :one
SELECT * FROM users WHERE username = $1;

-- name: ListUsers :many
SELECT * FROM users ORDER BY id;

-- name: AddUser :exec
INSERT INTO users (username, password, super_admin)
VALUES ($1, $2, $3);

-- name: ListDirectives :many
SELECT * FROM directives ORDER BY id DESC;

-- name: AddDirective :exec
WITH new_directive AS (
    INSERT INTO directives (selector_type, selector, directive_type, directive_data, applies_to)
    VALUES ($1, $2, $3, $4, $5)
    RETURNING id
)
INSERT INTO audit_log (user_id, note, action, directive)
VALUES ($6, $7, 'create', (select id from new_directive));
