"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, Invoice } from "@/lib/api";
import InvoiceForm from "@/components/invoices/InvoiceForm";

export default function EditInvoicePage() {
  const params = useParams();
  const id = params?.id as string;
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      api.getInvoice(id)
        .then((res) => setInvoice(res))
        .catch((err) => console.error("Error loading invoice:", err))
        .finally(() => setLoading(false));
    }
  }, [id]);

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-500">
        <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
        Loading invoice...
      </div>
    );
  }

  if (!invoice) {
    return (
      <div className="p-16 text-center text-slate-500">
        Invoice not found.
      </div>
    );
  }

  return <InvoiceForm initialData={invoice} isEdit={true} />;
}
