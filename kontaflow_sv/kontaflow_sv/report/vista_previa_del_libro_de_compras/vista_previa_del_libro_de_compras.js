frappe.query_reports["Vista previa del Libro de Compras"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Empresa"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
		},
		{
			fieldname: "mes",
			label: __("Mes"),
			fieldtype: "Data",
			description: __("AAAA-MM, por ejemplo 2026-09"),
			reqd: 1,
		},
	],
	formatter(value, row, column, data, default_formatter) {
		if (column.fieldtype === "Data") {
			value = frappe.utils.escape_html(value ?? "");
		}
		return default_formatter(value, row, column, data);
	},
};
