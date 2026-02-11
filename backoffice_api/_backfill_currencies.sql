UPDATE orders
SET origin_currency = CASE upper(origin_country)
  WHEN 'CHILE' THEN 'CLP'
  WHEN 'PERU' THEN 'PEN'
  WHEN 'USA' THEN 'USD'
  WHEN 'VENEZUELA' THEN 'VES'
  WHEN 'VE' THEN 'VES'
  WHEN 'COLOMBIA' THEN 'COP'
  WHEN 'ARGENTINA' THEN 'ARS'
  WHEN 'MEXICO' THEN 'MXN'
  ELSE origin_currency
END
WHERE origin_currency IS NULL;

UPDATE orders
SET dest_currency = CASE upper(dest_country)
  WHEN 'CHILE' THEN 'CLP'
  WHEN 'PERU' THEN 'PEN'
  WHEN 'USA' THEN 'USD'
  WHEN 'VENEZUELA' THEN 'VES'
  WHEN 'VE' THEN 'VES'
  WHEN 'COLOMBIA' THEN 'COP'
  WHEN 'ARGENTINA' THEN 'ARS'
  WHEN 'MEXICO' THEN 'MXN'
  ELSE dest_currency
END
WHERE dest_currency IS NULL;
