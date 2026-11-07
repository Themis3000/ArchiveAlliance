-- name: GetUser :one
SELECT * FROM users WHERE username = $1;

-- name: CheckUserEnabled :one
SELECT EXISTS(SELECT FROM users WHERE id = $1 AND enabled = true);

-- name: ListUsers :many
SELECT * FROM users ORDER BY id;

-- name: AddUser :exec
INSERT INTO users (username, password, super_admin)
VALUES ($1, $2, $3);

-- name: ListDirectives :many
SELECT * FROM directives ORDER BY id DESC;

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
SELECT * FROM audit_log WHERE directive = $1 ORDER BY id DESC;

-- name: GetDirective :one
SELECT * from directives WHERE id = $1;

-- name: GetTableCount :one
select count(*)
from information_schema.tables
where table_schema = 'public';

