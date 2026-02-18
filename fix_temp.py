with open('backoffice_web/src/app/orders/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregar useMemo al import
content = content.replace(
    "import React, { useState, useEffect, useCallback } from 'react';",
    "import React, { useState, useEffect, useCallback, useMemo } from 'react';"
)

# 2. Quitar estado filteredOrders
content = content.replace(
    "const [filteredOrders, setFilteredOrders] = useState<Order[]>([]);",
    ""
)

# 3. Quitar setFilteredOrders del fetch
content = content.replace(
    "      setOrders(ordersArray);\n      setFilteredOrders(ordersArray);",
    "      setOrders(ordersArray);"
)
content = content.replace(
    "      setOrders([]);\n      setFilteredOrders([]);",
    "      setOrders([]);"
)

# 4. Reemplazar useEffect de filtrado por useMemo
old_effect = '''  useEffect(() => {
    let filtered = [...orders];
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter((o) =>
        o.public_id.toString().includes(search) ||
        o.origin_country?.toLowerCase().includes(search) ||
        o.dest_country?.toLowerCase().includes(search) ||
        o.status?.toLowerCase().includes(search)
      );
    }
    if (statusFilter !== 'all') filtered = filtered.filter((o) => o.status === statusFilter);
    if (countryFilter !== 'all') filtered = filtered.filter((o) => o.origin_country === countryFilter || o.dest_country === countryFilter);
    setFilteredOrders(filtered);
  }, [searchTerm, statusFilter, countryFilter, orders]);'''

new_memo = '''  const filteredOrders = useMemo(() => {
    let filtered = [...orders];
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter((o) =>
        o.public_id.toString().includes(search) ||
        o.origin_country?.toLowerCase().includes(search) ||
        o.dest_country?.toLowerCase().includes(search) ||
        o.status?.toLowerCase().includes(search)
      );
    }
    if (statusFilter !== 'all') filtered = filtered.filter((o) => o.status === statusFilter);
    if (countryFilter !== 'all') filtered = filtered.filter((o) => o.origin_country === countryFilter || o.dest_country === countryFilter);
    return filtered;
  }, [searchTerm, statusFilter, countryFilter, orders]);'''

content = content.replace(old_effect, new_memo)

with open('backoffice_web/src/app/orders/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("OK - orders/page.tsx: useEffect reemplazado por useMemo")
