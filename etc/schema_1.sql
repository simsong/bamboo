INSERT INTO metadata (k,v) values ('schema_version',1) ON DUPLICATE KEY UPDATE id=id;
