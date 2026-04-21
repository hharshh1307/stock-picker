"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { UserProfile, InvestmentPlan } from "@/lib/types";
import { Trash2, Plus, Save } from "lucide-react";

export default function SettingsPage() {
  const [profile, setProfile] = useState<UserProfile>({ risk_tolerance: "medium", total_capital: 0, expected_returns: 0 });
  const [plans, setPlans] = useState<InvestmentPlan[]>([]);
  const [loading, setLoading] = useState(true);

  // New Plan form
  const [frequency, setFrequency] = useState("Weekly");
  const [amount, setAmount] = useState("");
  const [desc, setDesc] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [prof, pl] = await Promise.all([
        api.user.getProfile(),
        api.user.getPlans()
      ]);
      setProfile(prof);
      setPlans(pl);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const saveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.user.updateProfile(profile);
      alert("Profile saved successfully");
    } catch (err) {
      console.error(err);
    }
  };

  const addPlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount) return;

    try {
      await api.user.upsertPlan({
        frequency,
        allocated_amount: parseFloat(amount),
        description: desc
      });
      setAmount("");
      setDesc("");
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const deletePlan = async (id: number) => {
    try {
      await api.user.deletePlan(id);
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) return <div className="p-8">Loading...</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-12">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings & Plans</h1>
        <p className="text-zinc-400 mt-2">Configure your risk profile and recurring investment strategies.</p>
      </div>

      {/* User Profile Section */}
      <section className="space-y-6">
        <h2 className="text-xl font-semibold border-b border-zinc-800 pb-2">Investor Profile</h2>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
          <form onSubmit={saveProfile} className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm text-zinc-400 font-medium">Risk Tolerance</label>
                <select 
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500"
                  value={profile.risk_tolerance}
                  onChange={e => setProfile({...profile, risk_tolerance: e.target.value})}
                >
                  <option value="low">Low (Conservative)</option>
                  <option value="medium">Medium (Moderate)</option>
                  <option value="high">High (Aggressive)</option>
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm text-zinc-400 font-medium">Total Capital Base (₹)</label>
                <input 
                  type="number" 
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500"
                  value={profile.total_capital || ""}
                  onChange={e => setProfile({...profile, total_capital: parseFloat(e.target.value) || 0})}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm text-zinc-400 font-medium">Expected Annual Returns (%)</label>
                <input 
                  type="number" 
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500"
                  value={profile.expected_returns || ""}
                  onChange={e => setProfile({...profile, expected_returns: parseFloat(e.target.value) || 0})}
                />
              </div>
            </div>
            <button 
              type="submit"
              className="flex items-center gap-2 bg-zinc-100 hover:bg-white text-zinc-900 font-medium text-sm px-4 py-2 rounded-lg transition-colors"
            >
              <Save className="h-4 w-4" />
              Save Profile
            </button>
          </form>
        </div>
      </section>

      {/* Investment Plans Section */}
      <section className="space-y-6">
        <h2 className="text-xl font-semibold border-b border-zinc-800 pb-2">Investment Plans</h2>
        
        <div className="grid gap-6 md:grid-cols-2">
          {plans.map(plan => (
            <div key={plan.id} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="inline-flex items-center rounded-full bg-emerald-500/10 text-emerald-400 px-3 py-1 text-xs font-semibold">
                    {plan.frequency}
                  </span>
                  <button 
                    onClick={() => plan.id && deletePlan(plan.id)}
                    className="text-zinc-500 hover:text-red-400 transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                <div className="text-3xl font-bold tracking-tight mb-2">
                  ₹{plan.allocated_amount.toLocaleString('en-IN')}
                </div>
                <p className="text-sm text-zinc-400">{plan.description || "No description provided."}</p>
              </div>
            </div>
          ))}

          {/* Add New Plan Card */}
          <div className="rounded-xl border border-dashed border-zinc-700 bg-zinc-950 p-6">
            <h3 className="text-sm font-medium text-zinc-100 mb-4 flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Add New Plan
            </h3>
            <form onSubmit={addPlan} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-zinc-400 font-medium">Frequency</label>
                  <select 
                    className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500"
                    value={frequency}
                    onChange={e => setFrequency(e.target.value)}
                  >
                    <option value="Daily">Daily</option>
                    <option value="Weekly">Weekly</option>
                    <option value="Monthly">Monthly</option>
                    <option value="Yearly">Yearly</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-400 font-medium">Amount (₹)</label>
                  <input 
                    type="number" 
                    required
                    className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500"
                    value={amount}
                    onChange={e => setAmount(e.target.value)}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-xs text-zinc-400 font-medium">Description</label>
                <input 
                  type="text" 
                  placeholder="e.g. For momentum breakout trades"
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500"
                  value={desc}
                  onChange={e => setDesc(e.target.value)}
                />
              </div>
              <button 
                type="submit"
                className="w-full bg-zinc-800 hover:bg-zinc-700 text-white font-medium text-sm py-2 rounded-lg transition-colors"
              >
                Create Plan
              </button>
            </form>
          </div>
        </div>
      </section>
    </div>
  );
}
