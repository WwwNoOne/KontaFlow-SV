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
	onload(report) {
		report.page.add_inner_button(__("Exportar libro de compras (Excel)"), async () => {
			const { company, mes } = report.get_filter_values();
			if (!company || !mes) {
				frappe.msgprint(__("Indica la empresa y el mes para exportar el libro de compras."));
				return;
			}

			const mensajeError = __("No se pudo exportar el libro de compras.");
			try {
				const respuesta = await fetch("/api/method/kontaflow_sv.api.exportar_libro_compras", {
					method: "POST",
					headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
					body: new URLSearchParams({ company, mes }),
				});
				if (!respuesta.ok) {
					const error = await respuesta.json().catch(() => ({}));
					const mensajes = JSON.parse(error?._server_messages ?? "[]");
					const aviso =
						respuesta.status === 403
							? __("No tienes permiso para exportar el libro de compras.")
							: mensajeError;
					frappe.msgprint(mensajes.length ? { message: mensajes } : aviso);
					return;
				}

				const disposicion = respuesta.headers.get("Content-Disposition");
				const nombre = disposicion?.match(/;\s*filename\s*=\s*(?:"([^"]+)"|([^;]+))/i);
				if (!nombre) {
					frappe.msgprint(mensajeError);
					return;
				}

				const url = URL.createObjectURL(await respuesta.blob());
				const enlace = document.createElement("a");
				enlace.href = url;
				enlace.download = nombre[1] ?? nombre[2].trim();
				enlace.click();
				setTimeout(() => URL.revokeObjectURL(url), 1000);
			} catch {
				frappe.msgprint(mensajeError);
			}
		});
	},
	formatter(value, row, column, data, default_formatter) {
		if (column.fieldtype === "Data") {
			value = frappe.utils.escape_html(value ?? "");
		}
		return default_formatter(value, row, column, data);
	},
};
