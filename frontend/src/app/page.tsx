"use client";

import React, { useEffect, useState } from "react";
import { api, Invoice, Client, RecurringDashboardStatus } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import {
  FileText,
  AlertCircle,
  AlertTriangle,
  Users,
  PlusCircle,
  Calendar,
  Receipt,
  CheckCircle2,
  Printer,
  ChevronRight,
  Eye,
} from "lucide-react";

export default function DashboardPage() {
  const { user, isAccountant, isAdmin } = useAuth();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [summary, setSummary] = useState({
    total_billed: 0,
    total_collected: 0,
    total_due: 0,
    total_invoices: 0,
    active_clients: 0,
  });
  const [loading, setLoading] = useState(true);
  const [batchMonth, setBatchMonth] = useState("");
  const [batchModalOpen, setBatchModalOpen] = useState(false);
  const [batchSubmitting, setBatchSubmitting] = useState(false);
  const [batchMessage, setBatchMessage] = useState("");
  const [recurringStatus, setRecurringStatus] = useState<RecurringDashboardStatus | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [invRes, clientRes, summaryRes, recStatusRes] = await Promise.all([
        api.getInvoices({ page_size: 10 }),
        api.getClients(),
        api.getDashboardSummary().catch(() => null),
        api.getRecurringStatus().catch(() => null),
      ]);
      setInvoices(invRes.results || []);
      setClients(clientRes.results || []);
      if (summaryRes) {
        setSummary(summaryRes);
      }
      if (recStatusRes) {
        setRecurringStatus(recStatusRes);
      }
    } catch (err) {
      console.error("Dashboard fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const d = new Date();
    const monthNames = [
      "January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December"
    ];
    setBatchMonth(`${monthNames[d.getMonth()]}-${d.getFullYear()}`);
  }, []);

  const totalInvoiced = summary.total_billed;
  const totalPaid = summary.total_collected;
  const totalDue = summary.total_due;
  const activeClientsCount = summary.active_clients || clients.length;

  const handleGenerateBatch = async () => {
    if (!batchMonth) return;
    try {
      setBatchSubmitting(true);
      setBatchMessage("");
      const res = await api.generateMonthlyBills(batchMonth);
      setBatchMessage(res.message);
      await fetchData();
      setTimeout(() => {
        setBatchModalOpen(false);
        setBatchMessage("");
      }, 1500);
    } catch (err: any) {
      setBatchMessage(err.message || "Failed to generate monthly bills");
    } finally {
      setBatchSubmitting(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Recurring Run Warning Banner */}
      {recurringStatus?.has_warning && (
        <div className="p-4 md:p-5 rounded-3xl bg-amber-50 border border-amber-200/80 text-amber-900 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm">
          <div className="flex items-start gap-3">
            <AlertTriangle size={22} className="text-amber-600 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-sm">Automated Billing Alert</h4>
              <p className="text-xs text-amber-800 mt-0.5">{recurringStatus.warning_message}</p>
            </div>
          </div>
          {isAdmin && (
            <a
              href="/recurring-runs"
              className="px-4 py-2 rounded-xl text-xs font-bold bg-amber-200/70 hover:bg-amber-200 text-amber-950 transition-colors shrink-0 shadow-2xs"
            >
              Inspect & Run
            </a>
          )}
        </div>
      )}

      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-gradient-to-r from-white via-cyan-50/30 to-blue-50/50 p-6 md:p-8 rounded-3xl border border-cyan-200/60 shadow-[0_4px_24px_-6px_rgba(6,182,212,0.10)]">
        <div>
          <h2 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">
            Welcome back, {user?.username}! 👋
          </h2>
          <p className="text-slate-500 mt-1 text-sm md:text-base">
            Here is your subscription billing summary and recent invoice activity.
          </p>
        </div>

        {isAccountant && (
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => setBatchModalOpen(true)}
              className="px-4 py-2.5 rounded-xl font-semibold text-xs md:text-sm bg-white hover:bg-slate-50 text-slate-800 border border-slate-200 transition-all flex items-center gap-2 cursor-pointer shadow-xs hover:shadow-sm"
            >
              <Calendar size={17} className="text-cyan-700" />
              Batch Generate Bills
            </button>
            <a
              href="/invoices/new"
              className="px-4 py-2.5 rounded-xl font-bold text-xs md:text-sm bg-cyan-600 hover:bg-cyan-500 text-white transition-all flex items-center gap-2 cursor-pointer shadow-md shadow-cyan-600/20 hover:shadow-cyan-600/30"
            >
              <PlusCircle size={17} />
              Create New Bill
            </a>
          </div>
        )}
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="relative overflow-hidden p-6 rounded-3xl bg-gradient-to-br from-white via-blue-50/30 to-blue-50/70 border border-blue-200/70 shadow-[0_4px_20px_-4px_rgba(59,130,246,0.12)] hover:shadow-[0_8px_28px_-6px_rgba(59,130,246,0.22)] hover:-translate-y-1 transition-all duration-300">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-bold uppercase tracking-wider text-blue-700/80">Total Billed</span>
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 text-white flex items-center justify-center shadow-md shadow-blue-500/25">
              <Receipt size={20} />
            </div>
          </div>
          <div className="text-2xl md:text-3xl font-black text-slate-900">
            {totalInvoiced.toLocaleString()} <span className="text-sm font-semibold text-slate-500">Tk</span>
          </div>
          <p className="text-xs text-blue-700/70 font-medium mt-2">Sum of recent invoices</p>
        </div>

        <div className="relative overflow-hidden p-6 rounded-3xl bg-gradient-to-br from-white via-emerald-50/30 to-emerald-50/70 border border-emerald-200/70 shadow-[0_4px_20px_-4px_rgba(16,185,129,0.12)] hover:shadow-[0_8px_28px_-6px_rgba(16,185,129,0.22)] hover:-translate-y-1 transition-all duration-300">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-700/80">Collected</span>
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-600 text-white flex items-center justify-center shadow-md shadow-emerald-500/25">
              <CheckCircle2 size={20} />
            </div>
          </div>
          <div className="text-2xl md:text-3xl font-black text-emerald-700">
            {totalPaid.toLocaleString()} <span className="text-sm font-semibold text-emerald-600/70">Tk</span>
          </div>
          <p className="text-xs text-emerald-700/70 font-medium mt-2">Payments received to date</p>
        </div>

        <div className="relative overflow-hidden p-6 rounded-3xl bg-gradient-to-br from-white via-amber-50/30 to-amber-50/70 border border-amber-200/70 shadow-[0_4px_20px_-4px_rgba(245,158,11,0.14)] hover:shadow-[0_8px_28px_-6px_rgba(245,158,11,0.24)] hover:-translate-y-1 transition-all duration-300">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-700/80">Total Due</span>
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-amber-500 to-amber-600 text-white flex items-center justify-center shadow-md shadow-amber-500/25">
              <AlertCircle size={20} />
            </div>
          </div>
          <div className="text-2xl md:text-3xl font-black text-amber-700">
            {totalDue.toLocaleString()} <span className="text-sm font-semibold text-amber-600/70">Tk</span>
          </div>
          <p className="text-xs text-amber-700/70 font-medium mt-2">Pending collection</p>
        </div>

        <div className="relative overflow-hidden p-6 rounded-3xl bg-gradient-to-br from-white via-indigo-50/30 to-indigo-50/70 border border-indigo-200/70 shadow-[0_4px_20px_-4px_rgba(99,102,241,0.12)] hover:shadow-[0_8px_28px_-6px_rgba(99,102,241,0.22)] hover:-translate-y-1 transition-all duration-300">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-700/80">Active Clients</span>
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-indigo-500 to-indigo-600 text-white flex items-center justify-center shadow-md shadow-indigo-500/25">
              <Users size={20} />
            </div>
          </div>
          <div className="text-2xl md:text-3xl font-black text-slate-900">
            {activeClientsCount} <span className="text-sm font-semibold text-slate-500">companies</span>
          </div>
          <p className="text-xs text-indigo-700/70 font-medium mt-2">Subscribed to software</p>
        </div>
      </div>

      {/* Recent Invoices Table */}
      <div className="bg-white border border-slate-200/90 rounded-3xl overflow-hidden shadow-[0_4px_24px_-6px_rgba(0,0,0,0.06)]">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Recent Invoices</h3>
            <p className="text-xs text-slate-500 mt-0.5">Real-time status of client software bills</p>
          </div>
          <a
            href="/invoices"
            className="text-xs font-bold text-cyan-700 hover:text-cyan-800 flex items-center gap-1 transition-colors"
          >
            View All Invoices <ChevronRight size={15} />
          </a>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-400">
            <div className="w-8 h-8 border-2 border-cyan-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            Loading invoices...
          </div>
        ) : invoices.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            No invoices generated yet. Click "Create New Bill" to begin!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-700">
              <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 font-bold border-b border-slate-200">
                <tr>
                  <th className="py-3.5 px-6">Invoice #</th>
                  <th className="py-3.5 px-6">Client & Title</th>
                  <th className="py-3.5 px-6">Billing Month</th>
                  <th className="py-3.5 px-6 text-right">Payable</th>
                  <th className="py-3.5 px-6 text-right">Due</th>
                  <th className="py-3.5 px-6 text-center">Status</th>
                  <th className="py-3.5 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-4 px-6 font-mono text-xs font-bold text-cyan-700">
                      {inv.invoice_number}
                    </td>
                    <td className="py-4 px-6">
                      <div className="font-bold text-slate-900">{inv.client_name}</div>
                      <div className="text-xs text-slate-500 truncate max-w-xs">{inv.title}</div>
                    </td>
                    <td className="py-4 px-6 text-slate-500 text-xs">
                      {inv.billing_month || inv.issue_date}
                    </td>
                    <td className="py-4 px-6 text-right font-bold text-slate-900">
                      {parseFloat(inv.payable_amount).toLocaleString()} {inv.currency_symbol}
                    </td>
                    <td className="py-4 px-6 text-right font-bold text-amber-600">
                      {parseFloat(inv.due_amount).toLocaleString()} {inv.currency_symbol}
                    </td>
                    <td className="py-4 px-6 text-center">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold tracking-wide ${
                          inv.status === "PAID"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : inv.status === "PARTIALLY_PAID"
                            ? "bg-amber-50 text-amber-700 border border-amber-200"
                            : inv.status === "DRAFT"
                            ? "bg-slate-100 text-slate-700 border border-slate-200"
                            : "bg-rose-50 text-rose-700 border border-rose-200"
                        }`}
                      >
                        {inv.status === "PAID"
                          ? "Paid"
                          : inv.status === "PARTIALLY_PAID"
                          ? "Partially Paid"
                          : inv.status === "DRAFT"
                          ? "Draft"
                          : "Unpaid"}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right space-x-2">
                      <a
                        href={`/invoices/${inv.id}`}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition-colors"
                      >
                        <Printer size={13} />
                        View / Print
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Batch Bill Modal */}
      {batchModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white border border-slate-200 rounded-3xl p-6 md:p-8 max-w-md w-full shadow-2xl">
            <h3 className="text-xl font-bold text-slate-900 mb-2">Batch Generate Monthly Bills</h3>
            <p className="text-xs text-slate-500 mb-6">
              This will automatically create invoices for all active clients subscribed to software services for the specified month.
            </p>

            {batchMessage && (
              <div className="mb-4 p-3 rounded-xl bg-cyan-50 border border-cyan-200 text-cyan-800 text-xs font-medium">
                {batchMessage}
              </div>
            )}

            <div className="mb-6">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Billing Month (e.g. May-2026)
              </label>
              <input
                type="text"
                value={batchMonth}
                onChange={(e) => setBatchMonth(e.target.value)}
                placeholder="e.g. May-2026"
                className="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setBatchModalOpen(false)}
                className="px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={batchSubmitting || !batchMonth}
                onClick={handleGenerateBatch}
                className="px-5 py-2.5 rounded-xl text-xs font-bold bg-cyan-600 hover:bg-cyan-500 text-white transition-all flex items-center gap-2 disabled:opacity-50 cursor-pointer shadow-sm"
              >
                {batchSubmitting ? "Generating..." : "Generate Bills"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
