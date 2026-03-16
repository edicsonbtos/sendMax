const fs = require('fs');
const file = 'backoffice_web/src/app/page.tsx';
let data = fs.readFileSync(file, 'utf8');
data = data.replace(/formatter=\{\(value\?:unknown,name\?:string\)/g, 'formatter={(value: any, name: any)');
fs.writeFileSync(file, data);
