-- name: GetUser :one
SELECT * FROM users WHERE username = $1;

-- name: CheckUserEnabled :one
SELECT EXISTS(SELECT FROM users WHERE id = $1 AND enabled = true);

-- name: ListUsers :many
SELECT * FROM users ORDER BY id;

-- name: AddUser :exec
INSERT INTO users (username, password, super_admin)
VALUES ($1, $2, $3);

-- name: UpdateUser :exec
UPDATE users
SET enabled = $2, super_admin = $3
WHERE id = $1;

-- name: ListDirectives :many
SELECT * FROM directives
ORDER BY id DESC
OFFSET $1
LIMIT $2;

-- name: SearchDirectives :many
SELECT * FROM directives
WHERE selector = $1
ORDER BY id DESC;

-- name: AddDirectiveWithAudit :exec
WITH new_directive AS (
    INSERT INTO directives (selector_type, selector, directive_type, directive_data, applies_to)
    VALUES ($1, $2, $3, $4, $5)
    RETURNING id
)
INSERT INTO audit_log (user_id, note, action, directive)
VALUES ($6, $7, 'create', (select id from new_directive));

-- name: SetDirectiveStatus :exec
UPDATE directives
SET active = $2
WHERE id = $1;

-- name: AddAudit :exec
INSERT INTO audit_log (user_id, note, action, directive)
VALUES ($1, $2, $3, $4);

-- name: GetDirectiveAudits :many
SELECT a.id, a.action, a.note, a.user_id, a.time, u.username FROM audit_log a
LEFT JOIN users u on u.id = a.user_id
WHERE a.directive = $1;

-- name: GetDirective :one
SELECT * from directives WHERE id = $1;

-- name: GetTableCount :one
select count(*)
from information_schema.tables
where table_schema = 'public';

-- name: GetWorkDirectives :many
SELECT * from directives
WHERE
    (selector_type = 'work_id' AND selector = sqlc.arg(work_id)::text AND active = true AND applies_to IN (sqlc.arg(origin)::text, '*')) OR
    (selector_type = 'author' AND selector = any(sqlc.arg(authors)::text[]) AND active = true AND applies_to IN (sqlc.arg(origin)::text, '*'));
