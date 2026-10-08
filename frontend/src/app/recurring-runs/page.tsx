"use client";

import React, { useEffect, useState } from "react";
import {
  api,
  RecurringRun,
  RecurringPreviewResponse,
  RecurringDashboardStatus,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import {
  RefreshCw,
  Play,
  Eye,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Calendar,
  Clock,
  ArrowRight,
  ShieldAlert,
  FileText,
  X,
  Search,
} from "lucide-react";

export default function RecurringRunsPage() {
  const { isAdmin } = useAuth();
  const [runs, setRuns] = useState<RecurringRun[]>([]);
  const [statusInfo, setStatusInfo] = useState<RecurringDashboardStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Modals
  const [selectedRun, setSelectedRun] = useState<RecurringRun | null>(null);
  const [previewData, setPreviewData] = useState<RecurringPreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewPeriod, setPreviewPeriod] = useState("");

  const [triggerModalOpen, setTriggerModalOpen] = useState(false);
  const [triggerPeriod, setTriggerPeriod] = useState("");
  const [triggerSubmitting, setTriggerSubmitting] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      setErrorMsg("");
      const [runsRes, statRes] = await Promise.all([
        api.getRecurringRuns(),
        api.getRecurringStatus(),
      ]);
      setRuns(runsRes.results || []);
      setStatusInfo(statRes);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load recurring run data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleOpenPreview = async () => {
    try {
      setPreviewLoading(true);
      setPreviewModalOpen(true);
      const res = await api.previewRecurringRun(previewPeriod || undefined);
      setPreviewData(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to preview upcoming run.");
      setPreviewModalOpen(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleRefreshPreview = async (period: string) => {
    try {
      setPreviewLoading(true);
      const res = await api.previewRecurringRun(period || undefined);
      setPreviewData(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to preview run.");
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleTriggerRun = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setTriggerSubmitting(true);
      setErrorMsg("");
      setSuccessMsg("");
      const res = await api.triggerRecurringRun(triggerPeriod || undefined);
      setSuccessMsg(
        `Run completed! Created ${res.created_count} invoices, skipped ${res.skipped_count}, failed ${res.failed_count}.`
      );
      setTriggerModalOpen(false);
      setTriggerPeriod("");
      await fetchData();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to trigger recurring billing run.");
    } finally {
      setTriggerSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-400">
        <div className="w-8 h-8 border-2 border-cyan-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
        Loading recurring run history...
      </div>
    );
  }

  const totalRuns = runs.length;
  const successfulRuns = runs.filter((r) => r.status === "SUCCESS").length;
  const totalCreated = runs.reduce((acc, r) => acc + (r.created_count || 0), 0);

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Banner & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-gradient-to-r from-white via-cyan-50/20 to-blue-50/30 p-6 md:p-8 rounded-3xl border border-cyan-200/60 shadow-[0_4px_24px_-6px_rgba(6,182,212,0.08)]">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">
              Recurring Runs Audit
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-cyan-100 text-cyan-800 border border-cyan-200">
              Admin Only
            </span>
          </div>
          <p className="text-slate-500 mt-1 text-sm">
            Monitor automated subscription billing cycles, diagnose run errors, or trigger execution on demand.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleOpenPreview}
            className="px-4 py-2.5 rounded-xl font-bold text-xs md:text-sm bg-white hover:bg-slate-50 text-slate-800 border border-slate-200 transition-all flex items-center gap-2 cursor-pointer shadow-2xs hover:shadow-xs"
          >
            <Eye size={16} className="text-cyan-700" />
            Preview Next Run
          </button>

          <button
            type="button"
            onClick={() => setTriggerModalOpen(true)}
            className="px-4 py-2.5 rounded-xl font-bold text-xs md:text-sm bg-cyan-600 hover:bg-cyan-500 text-white transition-all flex items-center gap-2 cursor-pointer shadow-md shadow-cyan-600/20 hover:shadow-cyan-600/30"
          >
            <Play size={16} />
            Run Billing Now
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2 font-medium">
            <CheckCircle2 size={18} className="text-emerald-600 shrink-0" />
            {successMsg}
          </div>
          <button onClick={() => setSuccessMsg("")} className="text-emerald-700 hover:text-emerald-900 cursor-pointer">
            <X size={16} />
          </button>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2 font-medium">
            <AlertTriangle size={18} className="text-rose-600 shrink-0" />
            {errorMsg}
          </div>
          <button onClick={() => setErrorMsg("")} className="text-rose-700 hover:text-rose-900 cursor-pointer">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Warning Banner if missed or failed */}
      {statusInfo?.has_warning && (
        <div className="p-4 md:p-5 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 flex items-start gap-3 shadow-xs">
          <ShieldAlert size={22} className="text-amber-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-bold text-sm">Recurring Billing Warning</h4>
            <p className="text-xs text-amber-800">{statusInfo.warning_message}</p>
          </div>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-2xs">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Total Runs</span>
          <div className="text-2xl font-black text-slate-900 mt-2">{totalRuns}</div>
          <p className="text-[11px] text-slate-500 mt-1">Recorded executions</p>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-2xs">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Successful Runs</span>
          <div className="text-2xl font-black text-emerald-600 mt-2">{successfulRuns}</div>
          <p className="text-[11px] text-slate-500 mt-1">Completed without errors</p>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-2xs">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Total Billed Invoices</span>
          <div className="text-2xl font-black text-cyan-700 mt-2">{totalCreated}</div>
          <p className="text-[11px] text-slate-500 mt-1">Auto-generated to date</p>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-2xs">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Scheduler Schedule</span>
          <div className="text-sm font-bold text-slate-800 mt-2 flex items-center gap-1.5">
            <span
              className={`w-2 h-2 rounded-full ${
                statusInfo?.auto_billing_enabled ? "bg-emerald-500" : "bg-slate-300"
              }`}
            ></span>
            {statusInfo?.auto_billing_enabled ? "Active" : "Disabled"}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            Day {statusInfo?.auto_billing_day || 1} at {statusInfo?.auto_billing_time || "00:00"} ({statusInfo?.auto_billing_timezone})
          </p>
        </div>
      </div>

      {/* Runs Table */}
      <div className="bg-white border border-slate-200/90 rounded-3xl overflow-hidden shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-lg font-bold text-slate-900">Execution Log</h3>
          <span className="text-xs font-semibold text-slate-400">{runs.length} Runs logged</span>
        </div>

        {runs.length === 0 ? (
          <div className="p-16 text-center text-slate-400 text-sm">
            No recurring billing runs have been recorded yet. Click "Run Billing Now" to generate invoices on demand.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50/80 text-[11px] uppercase tracking-wider text-slate-500 font-bold border-b border-slate-200/70">
                <tr>
                  <th className="py-3.5 px-6">Run Time</th>
                  <th className="py-3.5 px-6">Trigger</th>
                  <th className="py-3.5 px-6">Period</th>
                  <th className="py-3.5 px-6">Status</th>
                  <th className="py-3.5 px-6 text-center">Created</th>
                  <th className="py-3.5 px-6 text-center">Skipped</th>
                  <th className="py-3.5 px-6 text-center">Failed</th>
                  <th className="py-3.5 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {runs.map((r) => {
                  const runDate = new Date(r.run_time);
                  return (
                    <tr key={r.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-4 px-6 font-semibold text-slate-800 whitespace-nowrap">
                        {runDate.toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}{" "}
                        <span className="text-xs text-slate-400 font-normal">
                          {runDate.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </td>

                      <td className="py-4 px-6">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                            r.trigger === "AUTO"
                              ? "bg-purple-50 text-purple-700 border border-purple-200"
                              : "bg-blue-50 text-blue-700 border border-blue-200"
                          }`}
                        >
                          {r.trigger === "AUTO" ? "Scheduled" : "Manual"}
                        </span>
                      </td>

                      <td className="py-4 px-6 font-mono text-xs font-bold text-slate-700">
                        {r.target_period || "-"}
                      </td>

                      <td className="py-4 px-6">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                            r.status === "SUCCESS"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : r.status === "PARTIAL"
                              ? "bg-amber-50 text-amber-700 border border-amber-200"
                              : "bg-rose-50 text-rose-700 border border-rose-200"
                          }`}
                        >
                          {r.status === "SUCCESS" && <CheckCircle2 size={13} />}
                          {r.status === "PARTIAL" && <AlertTriangle size={13} />}
                          {r.status === "FAILED" && <XCircle size={13} />}
                          {r.status}
                        </span>
                      </td>

                      <td className="py-4 px-6 text-center font-bold text-emerald-600">
                        {r.created_count}
                      </td>

                      <td className="py-4 px-6 text-center text-slate-500 font-medium">
                        {r.skipped_count}
                      </td>

                      <td className="py-4 px-6 text-center font-bold text-rose-600">
                        {r.failed_count}
                      </td>

                      <td className="py-4 px-6 text-right">
                        <button
                          type="button"
                          onClick={() => setSelectedRun(r)}
                          className="px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors cursor-pointer"
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Details Modal */}
      {selectedRun && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white border border-slate-200 rounded-3xl p-6 md:p-8 max-w-2xl w-full shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-5">
              <div>
                <h3 className="text-xl font-bold text-slate-900">Run Execution Details</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Target Period: <span className="font-bold text-slate-800">{selectedRun.target_period}</span> |{" "}
                  Trigger: <span className="font-bold text-slate-800">{selectedRun.trigger}</span>
                </p>
              </div>
              <button
                onClick={() => setSelectedRun(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                <X size={20} />
              </button>
            </div>

            {selectedRun.error_message && (
              <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs mb-5 font-mono">
                <strong>Error:</strong> {selectedRun.error_message}
              </div>
            )}

            {/* Created Invoices */}
            <div className="space-y-4">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-700 mb-2">
                  Created Invoices ({selectedRun.created_count})
                </h4>
                {selectedRun.details?.created && selectedRun.details.created.length > 0 ? (
                  <div className="max-h-44 overflow-y-auto border border-slate-200 rounded-xl divide-y divide-slate-100 text-xs">
                    {selectedRun.details.created.map((inv: any, idx: number) => {
                      const num = typeof inv === "string" ? inv : inv.invoice_number;
                      const client = typeof inv === "string" ? "" : inv.client_name;
                      const amount = typeof inv === "string" ? "" : `${inv.amount} Tk`;
                      return (
                        <div key={idx} className="p-2.5 flex items-center justify-between bg-slate-50/50">
                          <span className="font-mono font-bold text-slate-800">{num}</span>
                          <span className="text-slate-600">{client}</span>
                          <span className="font-bold text-emerald-700">{amount}</span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 italic">None created</p>
                )}
              </div>

              {/* Skipped Items */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                  Skipped Subscriptions ({selectedRun.skipped_count})
                </h4>
                {selectedRun.details?.skipped && selectedRun.details.skipped.length > 0 ? (
                  <div className="max-h-44 overflow-y-auto border border-slate-200 rounded-xl divide-y divide-slate-100 text-xs">
                    {selectedRun.details.skipped.map((sk: any, idx: number) => (
                      <div key={idx} className="p-2.5 flex items-center justify-between">
                        <span className="font-semibold text-slate-700">{sk.client_name}</span>
                        <span className="text-slate-400 text-[11px]">{sk.reason}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 italic">None skipped</p>
                )}
              </div>

              {/* Failed Items */}
              {selectedRun.details?.failed && selectedRun.details.failed.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-rose-700 mb-2">
                    Failed Subscriptions ({selectedRun.failed_count})
                  </h4>
                  <div className="max-h-44 overflow-y-auto border border-rose-200 rounded-xl divide-y divide-rose-100 text-xs bg-rose-50/30">
                    {selectedRun.details.failed.map((fl: any, idx: number) => (
                      <div key={idx} className="p-2.5 text-rose-800">
                        <div className="font-bold">{fl.client_name} (Sub #{fl.subscription_id})</div>
                        <div className="text-[11px] font-mono mt-0.5">{fl.error}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="mt-6 pt-4 border-t border-slate-100 flex justify-end">
              <button
                type="button"
                onClick={() => setSelectedRun(null)}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {previewModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white border border-slate-200 rounded-3xl p-6 md:p-8 max-w-3xl w-full shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-5">
              <div>
                <h3 className="text-xl font-bold text-slate-900">Preview Upcoming Billing Run</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Simulation of invoices that WOULD be created, without modifying the database.
                </p>
              </div>
              <button
                onClick={() => setPreviewModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                <X size={20} />
              </button>
            </div>

            {/* Period selector */}
            <div className="flex items-center gap-3 mb-5">
              <input
                type="text"
                placeholder="e.g. 2026-11 or November-2026 (blank for current)"
                value={previewPeriod}
                onChange={(e) => setPreviewPeriod(e.target.value)}
                className="px-4 py-2 bg-slate-50 border border-slate-300 rounded-xl text-xs w-64 focus:bg-white focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
              <button
                type="button"
                onClick={() => handleRefreshPreview(previewPeriod)}
                disabled={previewLoading}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors cursor-pointer"
              >
                {previewLoading ? "Simulating..." : "Simulate Period"}
              </button>
            </div>

            {previewLoading ? (
              <div className="p-12 text-center text-slate-400">
                <div className="w-6 h-6 border-2 border-cyan-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                Evaluating active subscriptions and billing rules...
              </div>
            ) : previewData ? (
              <div className="space-y-5">
                <div className="flex items-center gap-4 bg-slate-50 p-4 rounded-2xl border border-slate-200">
                  <div>
                    <span className="text-[11px] font-bold text-slate-400 uppercase">Target Period</span>
                    <div className="text-sm font-bold text-slate-800">
                      {previewData.target_period} ({previewData.display_month})
                    </div>
                  </div>
                  <div className="border-l border-slate-200 pl-4">
                    <span className="text-[11px] font-bold text-emerald-600 uppercase">Would Create</span>
                    <div className="text-sm font-black text-emerald-700">{previewData.total_would_create} Bills</div>
                  </div>
                  <div className="border-l border-slate-200 pl-4">
                    <span className="text-[11px] font-bold text-slate-400 uppercase">Would Skip</span>
                    <div className="text-sm font-bold text-slate-600">{previewData.total_would_skip} Subscriptions</div>
                  </div>
                </div>

                {/* Would Create List */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-700 mb-2">
                    Invoices That WOULD Be Created ({previewData.total_would_create})
                  </h4>
                  {previewData.would_create.length > 0 ? (
                    <div className="max-h-56 overflow-y-auto border border-emerald-200 rounded-xl divide-y divide-emerald-100 text-xs bg-emerald-50/20">
                      {previewData.would_create.map((item, idx) => (
                        <div key={idx} className="p-3 flex items-center justify-between">
                          <div>
                            <span className="font-bold text-slate-900">{item.client_name}</span>
                            <span className="text-slate-500 text-[11px] block">{item.service_name} ({item.billing_period})</span>
                          </div>
                          <div className="text-right">
                            <span className="font-bold text-emerald-700 block">{item.amount.toLocaleString()} Tk</span>
                            <span className="text-[10px] uppercase font-bold text-slate-400">{item.status}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 italic">No invoices due for creation in this period.</p>
                  )}
                </div>

                {/* Would Skip List */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                    Subscriptions Skipped ({previewData.total_would_skip})
                  </h4>
                  {previewData.would_skip.length > 0 ? (
                    <div className="max-h-40 overflow-y-auto border border-slate-200 rounded-xl divide-y divide-slate-100 text-xs">
                      {previewData.would_skip.map((item, idx) => (
                        <div key={idx} className="p-2.5 flex items-center justify-between">
                          <span className="font-semibold text-slate-700">{item.client_name}</span>
                          <span className="text-slate-400 text-[11px]">{item.reason}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 italic">None skipped.</p>
                  )}
                </div>
              </div>
            ) : null}

            <div className="mt-6 pt-4 border-t border-slate-100 flex justify-end">
              <button
                type="button"
                onClick={() => setPreviewModalOpen(false)}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 cursor-pointer"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Trigger Run Modal */}
      {triggerModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white border border-slate-200 rounded-3xl p-6 md:p-8 max-w-md w-full shadow-2xl">
            <h3 className="text-xl font-bold text-slate-900 mb-2">Trigger Billing Run</h3>
            <p className="text-xs text-slate-500 mb-5">
              This will immediately generate invoices for all active, due recurring subscriptions and catch up any missed cycles.
            </p>

            <form onSubmit={handleTriggerRun} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                  Target Billing Period (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. 2026-11 (leave blank for current)"
                  value={triggerPeriod}
                  onChange={(e) => setTriggerPeriod(e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 text-sm focus:bg-white focus:outline-none focus:ring-2 focus:ring-cyan-500"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Leave blank to auto-detect current period based on system timezone.
                </p>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setTriggerModalOpen(false)}
                  className="px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={triggerSubmitting}
                  className="px-5 py-2.5 rounded-xl text-xs font-bold bg-cyan-600 hover:bg-cyan-500 text-white transition-all flex items-center gap-2 cursor-pointer shadow-sm disabled:opacity-50"
                >
                  {triggerSubmitting ? "Executing Run..." : "Confirm & Run"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
