import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api';

export default function Dashboard() {
  const [groups, setGroups] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newGroup, setNewGroup] = useState({ name: '', description: '', members: '' });
  const navigate = useNavigate();

  useEffect(() => {
    loadGroups();
  }, []);

  const loadGroups = async () => {
    try {
      const res = await api.get('/groups/');
      setGroups(res.data.results || res.data);
    } catch {
      navigate('/login');
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    const memberNames = newGroup.members.split(',').map(n => n.trim()).filter(Boolean);
    const members = memberNames.map(name => ({
      display_name: name,
      joined_at: new Date().toISOString().split('T')[0],
    }));

    try {
      await api.post('/groups/', {
        name: newGroup.name,
        description: newGroup.description,
        members,
      });
      setShowCreate(false);
      setNewGroup({ name: '', description: '', members: '' });
      loadGroups();
    } catch (err) {
      alert('Failed to create group: ' + JSON.stringify(err.response?.data));
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  return (
    <div className="dashboard">
      <header className="topbar">
        <h1>Fair Share</h1>
        <button className="btn-secondary" onClick={handleLogout}>Logout</button>
      </header>

      <main className="container">
        <div className="section-header">
          <h2>Your Groups</h2>
          <button onClick={() => setShowCreate(!showCreate)}>+ New Group</button>
        </div>

        {showCreate && (
          <form className="create-form" onSubmit={handleCreate}>
            <input
              placeholder="Group name (e.g. Flat Expenses)"
              value={newGroup.name}
              onChange={(e) => setNewGroup({ ...newGroup, name: e.target.value })}
              required
            />
            <input
              placeholder="Description (optional)"
              value={newGroup.description}
              onChange={(e) => setNewGroup({ ...newGroup, description: e.target.value })}
            />
            <input
              placeholder="Members (comma-separated: Aisha, Rohan, Priya)"
              value={newGroup.members}
              onChange={(e) => setNewGroup({ ...newGroup, members: e.target.value })}
              required
            />
            <button type="submit">Create Group</button>
          </form>
        )}

        <div className="group-list">
          {groups.length === 0 && <p className="empty">No groups yet. Create one to get started!</p>}
          {groups.map(group => (
            <Link to={`/groups/${group.id}`} key={group.id} className="group-card">
              <h3>{group.name}</h3>
              <p>{group.description || 'No description'}</p>
              <span className="member-count">
                {group.memberships?.length || 0} members
              </span>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
