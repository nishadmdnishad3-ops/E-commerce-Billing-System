const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_superuser: boolean;
  role: "ADMIN" | "ACCOUNTANT" | "STAFF";
  phone: string;
}

export interface Company {
  id: number;
  name: string;
  tagline: string;
  address: string;
  website: string;
  email: string;
  phone: string;
  logo: string | null;
  authorization_signature: string | null;
  is_default: boolean;
}

export interface BankAccount {
  id: number;
  company: number;
  bank_name: string;
  account_name: string;
  account_number: string;
  branch_name: string;
  routing_number: string;
  is_default: boolean;
  is_active: boolean;
}

export interface GlobalSettings {
  id: number;
  currency_symbol: string;
  currency_code: string;
  default_company: number | null;
  default_bank_account: number | null;
  default_nb_text: string;
  invoice_footer_note: string;
}

export interface ClientServicePrice {
  id: number;
  client: number;
  service: number;
  service_name?: string;
  custom_name: string;
  custom_tech_specification: string;
  custom_price: string;
  is_active: boolean;
}

export interface Client {
  id: number;
  name: string;
  contact_person: string;
  phone: string;
  email: string;
  address: string;
  is_active: boolean;
  client_services?: ClientServicePrice[];
}

export interface Service {
  id: number;
  name: string;
  code: string;
  default_tech_specification: string;
  default_price: string;
  billing_cycle: "MONTHLY" | "QUARTERLY" | "YEARLY" | "ONE_TIME";
  is_active: boolean;
}

export interface InvoiceTemplate {
  id: number;
  name: string;
  title_pattern: string;
  invoice_number_prefix: string;
  nb_text: string;
  authorization_label: string;
  received_by_label: string;
  is_default: boolean;
}

export interface InvoiceItem {
  id?: number;
  sl: number;
  service?: number | null;
  item_name: string;
  technical_specification: string;
  quantity: string | number;
  unit_price: string | number;
  total?: string | number;
}

export interface Payment {
  id: number;
  invoice: number;
  amount: string;
  payment_date: string;
  payment_method: number | null;
  payment_method_name?: string;
  transaction_id: string;
  note: string;
  created_at: string;
}

export interface PaymentMethod {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  title: string;
  billing_month: string;
  issue_date: string;
  due_date: string | null;
  status: "DRAFT" | "ISSUED" | "PAID" | "PARTIALLY_PAID" | "CANCELLED";
  client: number;
  company: number;
  bank_account: number | null;
  template: number | null;
  
  // Snapshots
  company_name: string;
  company_tagline: string;
  company_address: string;
  company_website: string;
  company_email: string;
  company_phone: string;
  logo_url?: string | null;
  signature_url?: string | null;

  client_name: string;
  client_contact_person: string;
  client_address: string;
  client_phone: string;
  client_email: string;

  bank_name: string;
  account_name: string;
  account_number: string;
  branch_name: string;
  routing_number: string;
  nb_text: string;

  currency_symbol: string;
  sub_total: string;
  discount: string;
  vat_rate: string;
  vat_amount: string;
  payable_amount: string;
  advance_amount: string;
  paid_amount: string;
  due_amount: string;

  authorization_label: string;
  received_by_label: string;
  qr_code_url?: string | null;
  notes: string;
  items?: InvoiceItem[];
  payments?: Payment[];
  created_at: string;
}

class ApiService {
  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401 && typeof window !== "undefined") {
      // Token expired or invalid
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      let msg = errorData.error || errorData.detail;
      if (!msg && typeof errorData === "object" && Object.keys(errorData).length > 0) {
        msg = Object.entries(errorData)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : typeof v === "object" ? JSON.stringify(v) : v}`)
          .join(" | ");
      }
      throw new Error(msg || `Request failed with status ${response.status}`);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // Auth
  async login(username: string, password: string) {
    const res = await this.request<{ access: string; refresh: string }>("/auth/login/", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    localStorage.setItem("access_token", res.access);
    localStorage.setItem("refresh_token", res.refresh);
    return res;
  }

  logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>("/auth/me/");
  }

  // Generic helpers
  async get<T>(endpoint: string, params?: Record<string, string | number | boolean>): Promise<T> {
    let url = endpoint;
    if (params) {
      const query = new URLSearchParams();
      Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined && val !== null && val !== "") {
          query.append(key, String(val));
        }
      });
      const queryString = query.toString();
      if (queryString) {
        url += (url.includes("?") ? "&" : "?") + queryString;
      }
    }
    return this.request<T>(url, { method: "GET" });
  }

  async post<T>(endpoint: string, data: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async put<T>(endpoint: string, data: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async patch<T>(endpoint: string, data: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async delete(endpoint: string): Promise<any> {
    return this.request<any>(endpoint, { method: "DELETE" });
  }

  // Invoices
  async getInvoices(params?: any) {
    return this.get<{ count: number; results: Invoice[] }>("/invoices/", params);
  }

  async getInvoice(id: number | string) {
    return this.get<Invoice>(`/invoices/${id}/`);
  }

  async createInvoice(data: any) {
    return this.post<Invoice>("/invoices/", data);
  }

  async updateInvoice(id: number | string, data: any) {
    return this.put<Invoice>(`/invoices/${id}/`, data);
  }

  async deleteInvoice(id: number | string) {
    return this.delete(`/invoices/${id}/`);
  }

  async getInvoicePdfBlob(id: number | string): Promise<Blob> {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const res = await fetch(`${API_BASE_URL}/invoices/${id}/preview_pdf/`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!res.ok) {
      throw new Error(`Failed to generate PDF (${res.status})`);
    }
    return res.blob();
  }

  async downloadInvoicePdf(id: number | string, invoiceNumber?: string) {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const res = await fetch(`${API_BASE_URL}/invoices/${id}/download_pdf/`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!res.ok) {
      throw new Error(`Failed to download PDF (${res.status})`);
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Invoice_${invoiceNumber || id}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  async recordPayment(invoiceId: number, data: { amount: string | number; payment_method?: number; transaction_id?: string; note?: string; payment_date?: string }) {
    return this.post<{ message: string; payment: Payment; invoice: Invoice }>(`/invoices/${invoiceId}/record_payment/`, data);
  }

  async generateMonthlyBills(billing_month: string) {
    return this.post<{ message: string; generated_invoices: string[] }>("/invoices/generate_monthly_bills/", { billing_month });
  }

  // Clients
  async getClients() {
    return this.get<{ count: number; results: Client[] }>("/clients/?page_size=100");
  }

  async createClient(data: Partial<Client>) {
    return this.post<Client>("/clients/", data);
  }

  async updateClient(id: number, data: Partial<Client>) {
    return this.put<Client>(`/clients/${id}/`, data);
  }

  async deleteClient(id: number) {
    return this.delete(`/clients/${id}/`);
  }

  // Services
  async getServices() {
    return this.get<{ count: number; results: Service[] }>("/services/?page_size=100");
  }

  async createService(data: Partial<Service>) {
    return this.post<Service>("/services/", data);
  }

  async updateService(id: number, data: Partial<Service>) {
    return this.put<Service>(`/services/${id}/`, data);
  }

  async deleteService(id: number) {
    return this.delete(`/services/${id}/`);
  }

  // Client Services (Pricing)
  async saveClientService(data: Partial<ClientServicePrice>) {
    if (data.id) {
      return this.put<ClientServicePrice>(`/client-services/${data.id}/`, data);
    }
    return this.post<ClientServicePrice>("/client-services/", data);
  }

  // Companies & Banks
  async getCompanies() {
    return this.get<{ count: number; results: Company[] }>("/companies/");
  }

  async updateCompany(id: number, data: Partial<Company>) {
    return this.patch<Company>(`/companies/${id}/`, data);
  }

  async getBankAccounts() {
    return this.get<{ count: number; results: BankAccount[] }>("/bank-accounts/");
  }

  async createBankAccount(data: Partial<BankAccount>) {
    return this.post<BankAccount>("/bank-accounts/", data);
  }

  async updateBankAccount(id: number, data: Partial<BankAccount>) {
    return this.put<BankAccount>(`/bank-accounts/${id}/`, data);
  }

  // Settings & Templates
  async getSettings() {
    return this.get<{ count: number; results: GlobalSettings[] }>("/settings/");
  }

  async updateSettings(id: number, data: Partial<GlobalSettings>) {
    return this.patch<GlobalSettings>(`/settings/${id}/`, data);
  }

  async getTemplates() {
    return this.get<{ count: number; results: InvoiceTemplate[] }>("/templates/");
  }

  async updateTemplate(id: number, data: Partial<InvoiceTemplate>) {
    return this.put<InvoiceTemplate>(`/templates/${id}/`, data);
  }

  async getPaymentMethods() {
    return this.get<{ count: number; results: PaymentMethod[] }>("/payment-methods/");
  }
}

export const api = new ApiService();
