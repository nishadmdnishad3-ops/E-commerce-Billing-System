"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, Invoice } from "@/lib/api";
import { Printer, ArrowLeft, Edit, Download, Eye, X, Loader2 } from "lucide-react";

export default function InvoiceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(true);

  // PDF Preview & Download States
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  useEffect(() => {
    if (id) {
      api.getInvoice(id)
        .then((res) => setInvoice(res))
        .catch((err) => console.error("Error loading invoice:", err))
        .finally(() => setLoading(false));
    }
  }, [id]);

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadPdf = async () => {
    if (!invoice) return;
    try {
      setDownloadingPdf(true);
      await api.downloadInvoicePdf(invoice.id, invoice.invoice_number);
    } catch (err: any) {
      alert("Failed to download PDF: " + (err.message || "Unknown error"));
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleOpenPreview = async () => {
    if (!invoice) return;
    try {
      setLoadingPreview(true);
      setPreviewOpen(true);
      const blob = await api.getInvoicePdfBlob(invoice.id);
      const url = URL.createObjectURL(blob);
      setPreviewUrl(url);
    } catch (err: any) {
      alert("Failed to load PDF preview: " + (err.message || "Unknown error"));
      setPreviewOpen(false);
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleClosePreview = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
    setPreviewOpen(false);
  };

  const getMediaUrl = (url?: string | null) => {
    if (!url) return "";
    if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("data:")) {
      return url;
    }
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
    const host = apiBase.replace(/\/api\/?$/, "");
    return `${host}${url.startsWith("/") ? "" : "/"}${url}`;
  };

  const getVerificationUrl = () => {
    if (!invoice) return "https://www.raktch.com/";
    const website = (invoice.company_website || "www.raktch.com").trim();
    const base = website.startsWith("http") ? website : `https://${website}`;
    const cleanBase = base.endsWith("/") ? base : `${base}/`;
    return `${cleanBase}?invoice=${invoice.invoice_number || invoice.id}`;
  };

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-400">
        <div className="w-8 h-8 border-2 border-cyan-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
        Loading invoice document...
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

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-16">
      {/* Top Toolbar (Hidden on Print) */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-gradient-to-r from-white via-slate-50/50 to-white border border-slate-200/90 print:hidden shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)]">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/invoices")}
            className="p-2 rounded-xl bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer shadow-xs"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h3 className="font-bold text-slate-900 text-base">Invoice #{invoice.invoice_number}</h3>
            <span
              className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase mt-0.5 ${
                invoice.status === "PAID"
                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                  : invoice.status === "PARTIALLY_PAID"
                  ? "bg-amber-50 text-amber-700 border border-amber-200"
                  : "bg-blue-50 text-blue-700 border border-blue-200"
              }`}
            >
              {invoice.status}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <a
            href={`/invoices/${invoice.id}/edit`}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
          >
            <Edit size={14} />
            Edit Bill
          </a>

          {/* PDF Preview Button */}
          <button
            onClick={handleOpenPreview}
            disabled={loadingPreview}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-60 shadow-xs"
          >
            {loadingPreview ? <Loader2 size={14} className="animate-spin text-cyan-600" /> : <Eye size={14} className="text-cyan-600" />}
            Preview PDF
          </button>

          {/* Download PDF Button */}
          <button
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-cyan-700 hover:bg-cyan-800 text-white flex items-center gap-1.5 shadow-sm transition-all cursor-pointer disabled:opacity-60"
          >
            {downloadingPdf ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            Download PDF
          </button>

          {/* Browser Print Button */}
          <button
            onClick={handlePrint}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-cyan-600 hover:bg-cyan-500 text-white flex items-center gap-1.5 shadow-md shadow-cyan-600/20 transition-all cursor-pointer"
          >
            <Printer size={15} />
            Print
          </button>
        </div>
      </div>

      {/* Exact A4 Document Layout (Matches user's PDF invoice) */}
      <div className="invoice-paper bg-white text-slate-900 rounded-3xl shadow-[0_15px_40px_-5px_rgba(0,0,0,0.08)] p-8 md:p-12 border border-slate-200/90 print:p-0 print:border-none print:shadow-none print:rounded-none">
        {/* Top Header */}
        <div className="relative border-b-2 border-cyan-500 pb-4 mb-4">
          {/* Top Left Page Badge */}
          <div className="absolute top-0 left-0 bg-lime-500/20 text-lime-800 text-[10px] font-bold px-2 py-0.5 rounded">
            1
          </div>

          {/* Logo & Company Title */}
          <div className="text-center">
            <div className="flex justify-center mb-1.5">
              <img
                src={getMediaUrl(invoice.logo_url) || "/logo.jpg"}
                alt="RAKTCH Technology & Software"
                className="h-16 md:h-20 object-contain"
              />
            </div>
            <p className="text-[11px] text-slate-600 leading-tight">
              {invoice.company_address}
            </p>
            <p className="text-[11px] text-cyan-700 font-medium mt-0.5 space-x-2">
              <span className="text-blue-600 underline">{invoice.company_website}</span>
              <span>{invoice.company_email}</span>
              <span className="font-semibold text-slate-700">Phone: {invoice.company_phone}</span>
            </p>
          </div>
        </div>

        {/* Bill Title Banner */}
        <div className="text-center my-5">
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            {invoice.title}
          </h2>
        </div>

        {/* Client & Date Details */}
        <div className="flex justify-between items-start mb-6 text-sm">
          <div>
            <div className="font-bold text-slate-900 uppercase">
              NAME: <span className="font-semibold">{invoice.client_name}</span>
            </div>
            {invoice.client_address && (
              <div className="text-xs text-slate-600 mt-0.5 max-w-sm">{invoice.client_address}</div>
            )}
          </div>
          <div className="text-right">
            <div className="text-slate-800 font-semibold text-xs">
              Date: <span className="font-normal">{invoice.issue_date}</span>
            </div>
            <div className="text-slate-500 font-mono text-[11px] mt-0.5">
              Invoice #{invoice.invoice_number}
            </div>
          </div>
        </div>

        {/* Items Table */}
        <div className="border border-slate-700 mb-6">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-700 bg-slate-50 font-bold text-slate-900">
                <th className="py-2.5 px-3 border-r border-slate-700 w-12 text-center">SL</th>
                <th className="py-2.5 px-3 border-r border-slate-700 w-44">Name</th>
                <th className="py-2.5 px-3 border-r border-slate-700">Technical Specification</th>
                <th className="py-2.5 px-3 border-r border-slate-700 w-14 text-center">Qty</th>
                <th className="py-2.5 px-3 border-r border-slate-700 w-24 text-right">U Price (Tk)</th>
                <th className="py-2.5 px-3 w-28 text-right">Total (Tk)</th>
              </tr>
            </thead>
            <tbody>
              {invoice.items && invoice.items.length > 0 ? (
                invoice.items.map((item, idx) => (
                  <tr key={idx} className="border-b border-slate-700 align-top">
                    <td className="py-3 px-3 border-r border-slate-700 text-center font-medium">
                      {item.sl}
                    </td>
                    <td className="py-3 px-3 border-r border-slate-700 font-medium leading-relaxed">
                      {item.item_name}
                    </td>
                    <td className="py-3 px-3 border-r border-slate-700 leading-relaxed text-slate-700">
                      {item.technical_specification}
                    </td>
                    <td className="py-3 px-3 border-r border-slate-700 text-center">
                      {Number(item.quantity)}
                    </td>
                    <td className="py-3 px-3 border-r border-slate-700 text-right font-mono">
                      {Number(item.unit_price).toLocaleString()}
                    </td>
                    <td className="py-3 px-3 text-right font-mono font-semibold">
                      {Number(item.total).toLocaleString()}
                    </td>
                  </tr>
                ))
              ) : (
                <tr className="border-b border-slate-700">
                  <td colSpan={6} className="py-4 text-center text-slate-500">
                    No items listed
                  </td>
                </tr>
              )}

              {/* Subtotal Row */}
              <tr className="border-b border-slate-700 font-bold bg-slate-50/50">
                <td colSpan={3} className="py-2 px-3 border-r border-slate-700"></td>
                <td className="py-2 px-3 border-r border-slate-700 text-center font-medium">
                  {invoice.items?.reduce((acc, it) => acc + Number(it.quantity), 0) || 1}
                </td>
                <td className="py-2 px-3 border-r border-slate-700 text-right font-bold">
                  Sub Total
                </td>
                <td className="py-2 px-3 text-right font-mono font-bold">
                  {parseFloat(invoice.sub_total).toLocaleString()}
                </td>
              </tr>

              {/* Discount Row (If applicable) */}
              {parseFloat(invoice.discount) > 0 && (
                <tr className="border-b border-slate-700 text-slate-700">
                  <td colSpan={4} className="py-1.5 px-3 border-r border-slate-700"></td>
                  <td className="py-1.5 px-3 border-r border-slate-700 text-right font-semibold">
                    Discount
                  </td>
                  <td className="py-1.5 px-3 text-right font-mono">
                    -{parseFloat(invoice.discount).toLocaleString()}
                  </td>
                </tr>
              )}

              {/* VAT Row (If applicable) */}
              {parseFloat(invoice.vat_amount) > 0 && (
                <tr className="border-b border-slate-700 text-slate-700">
                  <td colSpan={4} className="py-1.5 px-3 border-r border-slate-700"></td>
                  <td className="py-1.5 px-3 border-r border-slate-700 text-right font-semibold">
                    VAT ({invoice.vat_rate}%)
                  </td>
                  <td className="py-1.5 px-3 text-right font-mono">
                    +{parseFloat(invoice.vat_amount).toLocaleString()}
                  </td>
                </tr>
              )}

              {/* Payable Amount Row */}
              <tr className="font-extrabold bg-slate-100 text-slate-900 border-b border-slate-700">
                <td colSpan={4} className="py-2.5 px-3 border-r border-slate-700"></td>
                <td className="py-2.5 px-3 border-r border-slate-700 text-right uppercase tracking-wider text-xs">
                  Payable Amount
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-sm">
                  {parseFloat(invoice.payable_amount).toLocaleString()}
                </td>
              </tr>

              {/* Advance / Paid Amount Row (If paid) */}
              {parseFloat(invoice.paid_amount) > 0 && (
                <tr className="border-b border-slate-700 text-emerald-800 font-semibold bg-emerald-50/40">
                  <td colSpan={4} className="py-1.5 px-3 border-r border-slate-700"></td>
                  <td className="py-1.5 px-3 border-r border-slate-700 text-right">
                    Paid / Received
                  </td>
                  <td className="py-1.5 px-3 text-right font-mono">
                    {parseFloat(invoice.paid_amount).toLocaleString()}
                  </td>
                </tr>
              )}

              {/* Due Amount Row */}
              {parseFloat(invoice.due_amount) > 0 && (
                <tr className="font-bold text-amber-900 bg-amber-50/50">
                  <td colSpan={4} className="py-2 px-3 border-r border-slate-700"></td>
                  <td className="py-2 px-3 border-r border-slate-700 text-right">
                    Net Due
                  </td>
                  <td className="py-2 px-3 text-right font-mono">
                    {parseFloat(invoice.due_amount).toLocaleString()}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Bank & Payment Instructions */}
        <div className="mb-14 text-xs text-slate-800 space-y-1">
          <p className="font-bold text-slate-900">{invoice.nb_text || "[N.B Please send the bill to]"}</p>
          <p className="font-bold text-sm text-blue-900">{invoice.bank_name}</p>
          <p>
            <span className="font-semibold">Account Name:</span> {invoice.account_name}
          </p>
          <p>
            <span className="font-semibold">Acc No:</span> <span className="font-bold font-mono">{invoice.account_number}</span>
          </p>
          <p>
            <span className="font-semibold">Branch Name:</span> {invoice.branch_name}
          </p>
          <p>
            <span className="font-semibold">Routing No:</span> <span className="font-mono">{invoice.routing_number}</span>
          </p>
        </div>

        {/* Authorization & Received Signatures */}
        <div className="flex justify-between items-end pt-12 pb-6 px-4">
          {/* Left Sign: Authorization */}
          <div className="text-center w-52">
            <div className="h-16 flex items-center justify-center">
              {invoice.signature_url ? (
                <img
                  src={getMediaUrl(invoice.signature_url)}
                  alt="Signature"
                  className="max-h-16 max-w-full object-contain"
                />
              ) : (
                <div className="font-serif italic text-blue-800 text-2xl font-bold tracking-wide">
                  Tanveg
                </div>
              )}
            </div>
            <div className="border-t border-slate-800 pt-1 font-semibold text-xs text-slate-900">
              {invoice.authorization_label || "Authorization"}
            </div>
          </div>

          {/* Right Sign: Received By */}
          <div className="text-center w-52">
            <div className="h-16"></div>
            <div className="border-t border-slate-800 pt-1 font-semibold text-xs text-slate-900">
              {invoice.received_by_label || "Received by"}
            </div>
          </div>
        </div>

        {/* Bottom Footer: QR Code & Website */}
        <div className="border-t border-slate-200 pt-4 mt-8 flex flex-wrap justify-between items-center gap-4 text-[11px] text-slate-500">
          <div className="flex items-center gap-3">
            <a
              href={getVerificationUrl()}
              target="_blank"
              rel="noopener noreferrer"
              title="Click to open verification URL or scan with phone camera"
              className="block p-1 rounded-lg border border-slate-200 hover:border-cyan-500 bg-white hover:shadow-md transition-all cursor-pointer group"
            >
              {invoice.qr_code_url ? (
                <img
                  src={getMediaUrl(invoice.qr_code_url)}
                  alt="Verification QR Code"
                  className="w-16 h-16 object-contain rounded group-hover:scale-105 transition-transform"
                />
              ) : (
                <div className="w-16 h-16 border border-slate-300 rounded p-1 flex items-center justify-center text-[9px] text-center font-mono">
                  QR CODE
                </div>
              )}
            </a>
            <div>
              <span className="font-semibold text-slate-800 text-xs block">
                Scan to verify bill authenticity
              </span>
              <a
                href={getVerificationUrl()}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] text-cyan-600 hover:text-cyan-700 hover:underline inline-flex items-center gap-1 mt-0.5"
              >
                <span>{invoice.company_website || "www.raktch.com"}</span>
                <span className="text-[10px]">&nearr;</span>
              </a>
            </div>
          </div>

          <div className="text-right">
            <a
              href={getVerificationUrl()}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-700 font-semibold hover:underline block text-xs"
            >
              {invoice.company_website || "www.raktch.com"}
            </a>
            <span className="text-[10px] text-slate-400 font-mono">
              Ref: #{invoice.invoice_number}
            </span>
          </div>
        </div>
      </div>

      {/* PDF Interactive Preview Modal */}
      {previewOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 sm:p-6 print:hidden">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-5xl h-[90vh] flex flex-col overflow-hidden animate-in fade-in duration-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-cyan-100 text-cyan-700 flex items-center justify-center">
                  <Eye size={18} />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-sm">PDF Document Preview</h3>
                  <p className="text-xs text-slate-500">Invoice #{invoice.invoice_number} (Server-generated PDF)</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleDownloadPdf}
                  disabled={downloadingPdf}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-cyan-700 hover:bg-cyan-800 text-white flex items-center gap-1.5 shadow-xs transition-colors cursor-pointer disabled:opacity-60"
                >
                  {downloadingPdf ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
                  Download PDF
                </button>
                <button
                  onClick={handleClosePreview}
                  className="p-1.5 rounded-lg hover:bg-slate-200 text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Modal Content / iFrame */}
            <div className="flex-1 bg-slate-100 p-2 sm:p-4 overflow-hidden relative">
              {loadingPreview ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/80 z-10 text-slate-500 gap-3">
                  <Loader2 size={32} className="animate-spin text-cyan-600" />
                  <span className="text-sm font-medium">Generating official PDF document...</span>
                </div>
              ) : previewUrl ? (
                <iframe
                  src={previewUrl}
                  title="PDF Preview"
                  className="w-full h-full rounded-xl border border-slate-300 shadow-inner bg-white"
                />
              ) : (
                <div className="flex items-center justify-center h-full text-slate-400 text-sm">
                  Failed to load preview.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
