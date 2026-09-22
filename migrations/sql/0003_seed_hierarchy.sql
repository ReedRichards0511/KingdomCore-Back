INSERT INTO archdioceses (id, name) VALUES
    ('01a0cb1e-c615-7da3-959a-22feee2c1b04', 'Arquidiócesis de Quito');

INSERT INTO vicariates (id, archdiocese_id, name, sector) VALUES
    (
        '01a0cb1e-c615-7da3-959a-2307d0726c0f',
        '01a0cb1e-c615-7da3-959a-22feee2c1b04',
        'Vicaría Episcopal Territorial Nuestra Señora de la Merced',
        'Sector extremo sur de Quito: Quito, Turubamba y Guamaní'
    );

INSERT INTO parishes (id, vicariate_id, name) VALUES
    (
        '01a0cb1e-c615-7da3-959a-23108e26edfb',
        '01a0cb1e-c615-7da3-959a-2307d0726c0f',
        'Parroquia Eclesiástica El Buen Pastor de Turubamba'
    );

INSERT INTO communities (id, parish_id, name) VALUES
    ('01a0cb1e-c615-7da3-959a-232f3fa458bd', '01a0cb1e-c615-7da3-959a-23108e26edfb', 'San Juan de Turubamba'),
    ('01a0cb1e-c615-7da3-959a-2338dcbff886', '01a0cb1e-c615-7da3-959a-23108e26edfb', 'Ecuador del Futuro'),
    ('01a0cb1e-c615-7da3-959a-234f09bc12f5', '01a0cb1e-c615-7da3-959a-23108e26edfb', 'Ciudad Jardín');
