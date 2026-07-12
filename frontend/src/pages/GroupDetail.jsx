import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';

export default function GroupDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [group, setGroup] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [balances, setBalances] = useState([]);
  const [debts, setDebts] = useState([]);
  const [tab, setTab] = useState('expenses');
  const [showAddExpense, setShowAddExpense] = useState(false);
  const [showAddMember, setShowAddMember] = useState(false);
  const [newMember, setNewMember] = useState({ display_name: '', joined_at: '' });
  const [newExpense, setNewExpense] = useState({
    description: '', paid_by: '', amount: '', currency: 'INR',
    date: new Date().toISOString().split('T')[0], split_type: 'equal',
    split_with: [], split_details: {}, notes: '',
  });
  const [editingMember, setEditingMember] = useState(null);


  useEffect(() => {
    loadGroup();
    loadExpenses();
    loadBalances();
    loadDebts();
  }, [id]);

  const loadGroup = async () => {
    try {
      const res = await api.get(`/groups/${id}/`);
      setGroup(res.data);
    } catch {
      navigate('/');
    }
  };

  const loadExpenses = async () => {
    const res = await api.get(`/groups/${id}/expenses/`);
    setExpenses(res.data.results || res.data);
  };

  const loadBalances = async () => {
    const res = await api.get(`/groups/${id}/balances/`);
    setBalances(res.data);
  };

  const loadDebts = async () => {
    const res = await api.get(`/groups/${id}/debts/`);
    setDebts(res.data);
  };

  const handleAddExpense = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/groups/${id}/expenses/`, {
        ...newExpense,
        amount: parseFloat(newExpense.amount),
        paid_by: parseInt(newExpense.paid_by),
        split_with: newExpense.split_with.map(Number),
      });
      setShowAddExpense(false);
      setNewExpense({
        description: '', paid_by: '', amount: '', currency: 'INR',
        date: new Date().toISOString().split('T')[0], split_type: 'equal',
        split_with: [], notes: '',
      });
      loadExpenses();
      loadBalances();
      loadDebts();
    } catch (err) {
      alert('Failed: ' + JSON.stringify(err.response?.data));
    }
  };

  const handleAddMember = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/groups/${id}/add-member/`, {
        display_name: newMember.display_name,
        joined_at: newMember.joined_at || new Date().toISOString().split('T')[0],
      });
      setShowAddMember(false);
      setNewMember({ display_name: '', joined_at: '' });
      loadGroup();
    } catch (err) {
      alert('Failed: ' + JSON.stringify(err.response?.data));
    }
  };

  const handleEditMember = async (e) => {
    e.preventDefault();
    try {
      await api.patch(`/groups/${id}/members/${editingMember.id}/`, {
        display_name: editingMember.display_name,
        joined_at: editingMember.joined_at,
        left_at: editingMember.left_at || null,
      });
      setEditingMember(null);
      loadGroup();
      loadBalances();
      loadDebts();
    } catch (err) {
      alert('Failed: ' + JSON.stringify(err.response?.data));
    }
  };

  const handleDeleteMember = async (memberId) => {
    if (!confirm('Are you sure you want to remove this member? This will delete all their records.')) return;
    try {
      await api.delete(`/groups/${id}/members/${memberId}/`);
      setEditingMember(null);
      loadGroup();
      loadBalances();
      loadDebts();
    } catch (err) {
      alert('Failed: ' + JSON.stringify(err.response?.data));
    }
  };

  const handleSettle = async (debt) => {
    try {
      await api.post(`/groups/${id}/payments/`, {
        from_member: debt.from_id,
        to_member: debt.to_id,
        amount: debt.amount,
        currency: 'INR',
        amount_inr: debt.amount,
        date: new Date().toISOString().split('T')[0],
        notes: 'Settlement',
      });
      loadBalances();
      loadDebts();
    } catch (err) {
      alert('Failed: ' + JSON.stringify(err.response?.data));
    }
  };

  const toggleSplitMember = (memberId) => {
    const current = newExpense.split_with;
    if (current.includes(memberId)) {
      setNewExpense({ ...newExpense, split_with: current.filter(id => id !== memberId) });
    } else {
      setNewExpense({ ...newExpense, split_with: [...current, memberId] });
    }
  };

  if (!group) return <div className="loading">Loading...</div>;

  return (
    <div className="dashboard">
      <header className="topbar">
        <button className="btn-back" onClick={() => navigate('/')}>← Back</button>
        <h1>{group.name}</h1>
        <div></div>
      </header>

      <main className="container">
        <div className="members-bar">
          <strong>Members:</strong>
          {group.memberships?.map(m => (
            <span
              key={m.id}
              className={`member-tag ${m.left_at ? 'inactive' : ''}`}
              style={{ cursor: 'pointer' }}
              onClick={() => setEditingMember({ ...m, left_at: m.left_at || '' })}
              title="Click to edit member"
            >
              {m.display_name}
              {m.left_at && <small> (left {m.left_at})</small>}
              <span style={{ marginLeft: '6px', opacity: 0.7, fontSize: '9px' }}>✏️</span>
            </span>
          ))}
          <button className="btn-small" onClick={() => { setShowAddMember(!showAddMember); setEditingMember(null); }}>+ Add</button>
        </div>

        {showAddMember && (
          <form className="create-form inline-form" onSubmit={handleAddMember}>
            <input placeholder="Name" value={newMember.display_name} onChange={e => setNewMember({...newMember, display_name: e.target.value})} required />
            <input type="date" placeholder="Joined At" value={newMember.joined_at} onChange={e => setNewMember({...newMember, joined_at: e.target.value})} />
            <button type="submit">Add Member</button>
          </form>
        )}

        {editingMember && (
          <form className="create-form" onSubmit={handleEditMember} style={{ borderLeft: '3px solid var(--primary)' }}>
            <h4 style={{ marginBottom: '10px' }}>Edit Member: {editingMember.display_name}</h4>
            <div className="row">
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Name</label>
                <input placeholder="Name" value={editingMember.display_name} onChange={e => setEditingMember({...editingMember, display_name: e.target.value})} required />
              </div>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Joined Date</label>
                <input type="date" value={editingMember.joined_at || ''} onChange={e => setEditingMember({...editingMember, joined_at: e.target.value})} required />
              </div>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Left Date (optional)</label>
                <input type="date" value={editingMember.left_at || ''} onChange={e => setEditingMember({...editingMember, left_at: e.target.value})} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
              <button type="submit" className="btn-small btn-approve">Save</button>
              <button type="button" className="btn-small btn-secondary" onClick={() => setEditingMember(null)}>Cancel</button>
              <button type="button" className="btn-small btn-skip" onClick={() => handleDeleteMember(editingMember.id)}>Remove Member</button>
            </div>
          </form>
        )}

        <div className="tabs">
          <button className={tab === 'expenses' ? 'active' : ''} onClick={() => setTab('expenses')}>Expenses</button>
          <button className={tab === 'balances' ? 'active' : ''} onClick={() => setTab('balances')}>Balances</button>
          <button className={tab === 'settle' ? 'active' : ''} onClick={() => setTab('settle')}>Settle Up</button>
          <button className={tab === 'import' ? 'active' : ''} onClick={() => setTab('import')}>Import CSV</button>
        </div>

        {tab === 'expenses' && (
          <div className="tab-content">
            <button onClick={() => setShowAddExpense(!showAddExpense)}>+ Add Expense</button>

            {showAddExpense && (
              <form className="create-form" onSubmit={handleAddExpense}>
                <input placeholder="Description" value={newExpense.description} onChange={e => setNewExpense({...newExpense, description: e.target.value})} required />
                <select value={newExpense.paid_by} onChange={e => setNewExpense({...newExpense, paid_by: e.target.value})} required>
                  <option value="">Who paid?</option>
                  {group.memberships?.map(m => <option key={m.id} value={m.id}>{m.display_name}</option>)}
                </select>
                <div className="row">
                  <input type="number" step="0.01" placeholder="Amount" value={newExpense.amount} onChange={e => setNewExpense({...newExpense, amount: e.target.value})} required />
                  <select value={newExpense.currency} onChange={e => setNewExpense({...newExpense, currency: e.target.value})}>
                    <option value="INR">INR</option>
                    <option value="USD">USD</option>
                  </select>
                </div>
                <input type="date" value={newExpense.date} onChange={e => setNewExpense({...newExpense, date: e.target.value})} />
                <select value={newExpense.split_type} onChange={e => setNewExpense({...newExpense, split_type: e.target.value})}>
                  <option value="equal">Equal</option>
                  <option value="unequal">Unequal</option>
                  <option value="percentage">Percentage</option>
                  <option value="share">By shares</option>
                </select>
                <div className="split-members">
                  <label>Split with:</label>
                  {group.memberships?.map(m => (
                    <label key={m.id} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={newExpense.split_with.includes(m.id)}
                        onChange={() => toggleSplitMember(m.id)}
                      />
                      {m.display_name}
                    </label>
                  ))}
                </div>

                {newExpense.split_type !== 'equal' && newExpense.split_with.length > 0 && (
                  <div className="split-details-section" style={{ margin: '15px 0', padding: '15px', background: 'var(--surface-hover)', borderRadius: 'var(--radius)' }}>
                    <label style={{ display: 'block', marginBottom: '10px', fontWeight: '600' }}>
                      Specify {newExpense.split_type === 'percentage' ? 'Percentages (%)' : newExpense.split_type === 'share' ? 'Shares (Ratios)' : 'Exact Amounts'} for selected members:
                    </label>
                    {newExpense.split_with.map(memberId => {
                      const member = group.memberships.find(m => m.id === memberId);
                      if (!member) return null;
                      return (
                        <div key={memberId} className="row" style={{ alignItems: 'center', marginBottom: '8px' }}>
                          <span style={{ flex: 2 }}>{member.display_name}</span>
                          <input
                            type="number"
                            step="any"
                            placeholder={newExpense.split_type === 'percentage' ? 'e.g. 25' : newExpense.split_type === 'share' ? 'e.g. 1' : 'Amount'}
                            value={newExpense.split_details[memberId] || ''}
                            onChange={e => {
                              const val = e.target.value;
                              setNewExpense(prev => ({
                                ...prev,
                                split_details: {
                                  ...prev.split_details,
                                  [memberId]: val
                                }
                              }));
                            }}
                            style={{ flex: 3, marginBottom: 0 }}
                            required
                          />
                        </div>
                      );
                    })}
                  </div>
                )}

                <textarea placeholder="Notes (optional)" value={newExpense.notes} onChange={e => setNewExpense({...newExpense, notes: e.target.value})} />
                <button type="submit">Add Expense</button>
              </form>
            )}

            <div className="expense-list">
              {expenses.length === 0 && <p className="empty">No expenses yet.</p>}
              {expenses.map(exp => (
                <div key={exp.id} className="expense-card">
                  <div className="expense-header">
                    <strong>{exp.description}</strong>
                    <span className="expense-amount">
                      {exp.currency} {parseFloat(exp.amount).toLocaleString()}
                    </span>
                  </div>
                  <div className="expense-meta">
                    Paid by {exp.paid_by_name} on {exp.date} · {exp.split_type} split
                  </div>
                  {exp.splits && (
                    <div className="expense-splits">
                      {exp.splits.map(s => (
                        <span key={s.id} className="split-chip">
                          {s.member_name}: ₹{parseFloat(s.share_amount_inr).toLocaleString()}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'balances' && (
          <div className="tab-content">
            <h3>Member Balances</h3>
            <table className="balance-table">
              <thead>
                <tr><th>Member</th><th>Paid</th><th>Owes</th><th>Net</th></tr>
              </thead>
              <tbody>
                {balances.map(b => (
                  <tr key={b.member_id}>
                    <td>{b.member_name}</td>
                    <td>₹{parseFloat(b.total_paid).toLocaleString()}</td>
                    <td>₹{parseFloat(b.total_owed).toLocaleString()}</td>
                    <td className={parseFloat(b.net_balance) >= 0 ? 'positive' : 'negative'}>
                      ₹{parseFloat(b.net_balance).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'settle' && (
          <div className="tab-content">
            <h3>Simplified Debts</h3>
            {debts.length === 0 && <p className="empty">All settled up! 🎉</p>}
            {debts.map((d, i) => (
              <div key={i} className="debt-card">
                <div className="debt-info">
                  <strong>{d.from_name}</strong> pays <strong>{d.to_name}</strong>
                  <span className="debt-amount">₹{parseFloat(d.amount).toLocaleString()}</span>
                </div>
                <button className="btn-settle" onClick={() => handleSettle(d)}>Mark Settled</button>
              </div>
            ))}
          </div>
        )}

        {tab === 'import' && <ImportTab groupId={id} onDone={() => { loadExpenses(); loadBalances(); loadDebts(); }} />}
      </main>
    </div>
  );
}

function ImportTab({ groupId, onDone }) {
  const [file, setFile] = useState(null);
  const [exchangeRate, setExchangeRate] = useState('85.0');
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('group_id', groupId);
    formData.append('exchange_rate_usd', exchangeRate);

    try {
      const res = await api.post('/import/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setSession(res.data);
    } catch (err) {
      alert('Upload failed: ' + JSON.stringify(err.response?.data));
    }
    setLoading(false);
  };

  const handleSkipRow = async (rowId) => {
    await api.patch(`/import/${session.id}/rows/${rowId}/`, { status: 'skipped' });
    const res = await api.get(`/import/${session.id}/`);
    setSession(res.data);
  };

  const handleApproveRow = async (rowId) => {
    await api.patch(`/import/${session.id}/rows/${rowId}/`, { status: 'ok' });
    const res = await api.get(`/import/${session.id}/`);
    setSession(res.data);
  };

  const handleCommit = async () => {
    try {
      const res = await api.post(`/import/${session.id}/commit/`);
      alert(`Import committed! ${res.data.expenses_created} expenses, ${res.data.payments_created} payments created, ${res.data.rows_skipped} skipped.`);
      setSession(null);
      onDone();
    } catch (err) {
      alert('Commit failed: ' + JSON.stringify(err.response?.data));
    }
  };

  if (!session) {
    return (
      <div className="tab-content">
        <h3>Import Expenses from CSV/XLSX</h3>
        <form className="create-form" onSubmit={handleUpload}>
          <input type="file" accept=".csv,.xlsx,.xls" onChange={e => setFile(e.target.files[0])} required />
          <div className="row">
            <label>USD→INR Rate:</label>
            <input type="number" step="0.01" value={exchangeRate} onChange={e => setExchangeRate(e.target.value)} />
          </div>
          <button type="submit" disabled={loading}>{loading ? 'Parsing...' : 'Upload & Parse'}</button>
        </form>
      </div>
    );
  }

  const flaggedRows = session.rows?.filter(r => r.anomalies?.length > 0) || [];
  const okRows = session.rows?.filter(r => r.anomalies?.length === 0) || [];

  return (
    <div className="tab-content">
      <h3>Import Review</h3>
      <div className="import-summary">
        <span>{session.rows?.length || 0} rows parsed</span>
        <span className="anomaly-badge">{session.anomaly_count} anomalies detected</span>
      </div>

      {flaggedRows.length > 0 && (
        <>
          <h4>⚠️ Flagged Rows ({flaggedRows.length})</h4>
          {flaggedRows.map(row => (
            <div key={row.id} className={`import-row ${row.status}`}>
              <div className="import-row-header">
                <strong>Row {row.row_number}: {row.raw_data?.description}</strong>
                <span>{row.raw_data?.currency} {row.raw_data?.amount}</span>
                <span className={`status-badge ${row.status}`}>{row.status}</span>
              </div>
              {row.anomalies?.map(a => (
                <div key={a.id} className={`anomaly ${a.severity}`}>
                  <span className="anomaly-type">{a.anomaly_type.replace(/_/g, ' ')}</span>
                  <p>{a.description}</p>
                  {a.auto_resolution && <p className="resolution">Auto: {a.auto_resolution}</p>}
                </div>
              ))}
              <div className="import-row-actions">
                <button className="btn-small btn-approve" onClick={() => handleApproveRow(row.id)}>✓ Keep</button>
                <button className="btn-small btn-skip" onClick={() => handleSkipRow(row.id)}>✗ Skip</button>
              </div>
            </div>
          ))}
        </>
      )}

      {okRows.length > 0 && (
        <>
          <h4>✅ Clean Rows ({okRows.length})</h4>
          <div className="clean-rows-summary">
            {okRows.map(row => (
              <div key={row.id} className="import-row-mini">
                <span>{row.raw_data?.description}</span>
                <span>{row.raw_data?.currency} {row.raw_data?.amount}</span>
              </div>
            ))}
          </div>
        </>
      )}

      <button className="btn-commit" onClick={handleCommit}>
        Commit Import ({session.rows?.filter(r => r.status !== 'skipped').length} rows)
      </button>
    </div>
  );
}
