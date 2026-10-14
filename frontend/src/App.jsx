
import { useEffect, useState } from 'react';
import './App.css';

const API_BASE_URL = 'http://127.0.0.1:8001';

// Retry a dead-letter delivery through the backend API.
async function retryDelivery(deliveryId) {
  const response = await fetch(
    `${API_BASE_URL}/deliveries/${deliveryId}/retry`,
    {
      method: 'POST',
    }
  );

  if (!response.ok) {
    let message = `Retry failed: HTTP ${response.status}`;

    try {
      const data = await response.json();
      message = data.detail || data.message || message;
    } catch {
      // Keep the default error message if the response is not JSON.
    }

    throw new Error(message);
  }

  return response.json();
}

function App() {
  const [activePage, setActivePage] = useState('Overview');

  // Delivery state
  const [deliveries, setDeliveries] = useState([]);
  const [deliveryTotal, setDeliveryTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retryingId, setRetryingId] = useState(null);
  const [retryMessage, setRetryMessage] = useState('');

  // Webhook state
  const [webhooks, setWebhooks] = useState([]);
  const [webhooksLoading, setWebhooksLoading] = useState(true);
  const [webhooksError, setWebhooksError] = useState('');

  // Event state
  const [events, setEvents] = useState([]);
  const [eventsLoading, setEventsLoading] = useState(true);
  const [eventsError, setEventsError] = useState('');

  const menuItems = ['Overview', 'Webhooks', 'Events', 'Deliveries'];

  const menuIcons = {
    Overview: '▦',
    Webhooks: '↗',
    Events: '◈',
    Deliveries: '⇄',
  };

  // Fetch delivery records
  async function fetchDeliveries() {
    const response = await fetch(
      `${API_BASE_URL}/deliveries/?limit=100&offset=0`
    );

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();

    setDeliveries(data.deliveries || []);
    setDeliveryTotal(data.total ?? 0);
    setError('');
  }

  useEffect(() => {
    async function loadDeliveries() {
      try {
        await fetchDeliveries();
      } catch (err) {
        console.error('Failed to fetch deliveries:', err);
        setError(
          'Could not load delivery data. Check your backend and CORS settings.'
        );
      } finally {
        setLoading(false);
      }
    }

    loadDeliveries();
  }, []);

  // Fetch registered webhooks
  useEffect(() => {
    async function fetchWebhooks() {
      try {
        const response = await fetch(`${API_BASE_URL}/webhooks`);

        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        setWebhooks(data.webhooks || []);
        setWebhooksError('');
      } catch (err) {
        console.error('Failed to fetch webhooks:', err);
        setWebhooksError('Could not load registered webhooks.');
      } finally {
        setWebhooksLoading(false);
      }
    }

    fetchWebhooks();
  }, []);

  // Fetch events
  useEffect(() => {
    async function fetchEvents() {
      try {
        const response = await fetch(`${API_BASE_URL}/events`);

        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        setEvents(data.events || []);
        setEventsError('');
      } catch (err) {
        console.error('Failed to fetch events:', err);
        setEventsError(
          'Could not load events. Check the backend and CORS settings.'
        );
      } finally {
        setEventsLoading(false);
      }
    }

    fetchEvents();
  }, []);

  // Retry a delivery, then refresh the delivery records.
  async function handleRetry(deliveryId) {
    setRetryingId(deliveryId);
    setRetryMessage('');

    try {
      const result = await retryDelivery(deliveryId);

      await fetchDeliveries();

      setRetryMessage(
        result.message || `Retry request for delivery #${deliveryId} succeeded.`
      );
    } catch (err) {
      console.error('Failed to retry delivery:', err);
      setRetryMessage(
        `Could not retry delivery #${deliveryId}: ${err.message}`
      );
    } finally {
      setRetryingId(null);
    }
  }

  const successfulDeliveries = deliveries.filter(
    (delivery) => delivery.status === 'success'
  ).length;

  const failedDeliveries = deliveries.filter(
    (delivery) =>
      delivery.status === 'failed' ||
      delivery.status === 'dead_letter'
  ).length;

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">W</div>

          <div>
            <h5>Webhook Platform</h5>
            <small>EVENT DELIVERY SYSTEM</small>
          </div>
        </div>

        <p className="menu-heading">WORKSPACE</p>

        <nav>
          {menuItems.map((item) => (
            <button
              key={item}
              type="button"
              className={`nav-item ${
                activePage === item ? 'active' : ''
              }`}
              onClick={() => setActivePage(item)}
            >
              <span>{menuIcons[item]}</span>
              {item}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="online-dot" />
          API Service
          <span className="online-label">
            {error ? 'CHECK' : loading ? 'LOADING' : 'CONNECTED'}
          </span>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="breadcrumb">
              Workspace / {activePage}
            </p>
            <h3>{activePage}</h3>
          </div>

          <div className="system-status">
            <span
              className="online-dot"
              style={{
                background: error ? '#ff6878' : '#2cdda6',
              }}
            />
            {error ? 'Connection issue' : 'API status'}
          </div>
        </header>

        {error && (
          <div className="api-error" role="alert">
            {error}
          </div>
        )}

        {activePage === 'Overview' && (
          <Overview
            deliveries={deliveries}
            deliveryTotal={deliveryTotal}
            successfulDeliveries={successfulDeliveries}
            failedDeliveries={failedDeliveries}
            loading={loading}
          />
        )}

        {activePage === 'Webhooks' && (
          <WebhooksPage
            webhooks={webhooks}
            loading={webhooksLoading}
            error={webhooksError}
          />
        )}

        {activePage === 'Events' && (
          <EventsPage
            events={events}
            loading={eventsLoading}
            error={eventsError}
          />
        )}

        {activePage === 'Deliveries' && (
          <DeliveriesPage
            deliveries={deliveries}
            loading={loading}
            onRetry={handleRetry}
            retryingId={retryingId}
            retryMessage={retryMessage}
          />
        )}
      </main>
    </div>
  );
}

// Dashboard overview
function Overview({
  deliveries,
  deliveryTotal,
  successfulDeliveries,
  failedDeliveries,
  loading,
}) {
  const stats = [
    {
      label: 'Total Deliveries',
      value: deliveryTotal,
      color: 'purple',
      icon: '⇄',
      description: 'Across all delivery records',
    },
    {
      label: 'Successful (loaded)',
      value: successfulDeliveries,
      color: 'green',
      icon: '✓',
      description: 'Successful records in this batch',
    },
    {
      label: 'Failed (loaded)',
      value: failedDeliveries,
      color: 'red',
      icon: '!',
      description: 'Failed or dead-letter records',
    },
    {
      label: 'Records Loaded',
      value: deliveries.length,
      color: 'blue',
      icon: '◈',
      description: 'Records fetched from the API',
    },
  ];

  return (
    <>
      <section className="stats-grid">
        {stats.map((stat) => (
          <div className="stat-card" key={stat.label}>
            <div className="stat-top">
              <span>{stat.label}</span>
              <span className={`stat-icon ${stat.color}`}>
                {stat.icon}
              </span>
            </div>

            <h2>
              {loading ? '…' : stat.value.toLocaleString()}
            </h2>

            <p>{stat.description}</p>
          </div>
        ))}
      </section>

      <section className="content-panel">
        <div className="panel-header">
          <div>
            <h4>Recent Delivery Activity</h4>
            <p>
              Monitor the latest delivery attempts returned by your API.
            </p>
          </div>

          <span className="live-badge">
            {loading ? 'LOADING' : 'API CONNECTED'}
          </span>
        </div>

        {loading ? (
          <div className="empty-state">
            <h5>Loading delivery records…</h5>
          </div>
        ) : deliveries.length === 0 ? (
          <div className="empty-state">
            <h5>No delivery records found</h5>
            <p>New delivery records will appear here.</p>
          </div>
        ) : (
          <DeliveryTable deliveries={deliveries.slice(0, 10)} />
        )}
      </section>
    </>
  );
}

// Deliveries page
function DeliveriesPage({
  deliveries,
  loading,
  onRetry,
  retryingId,
  retryMessage,
}) {
  return (
    <section className="content-panel">
      <div className="panel-header">
        <div>
          <h4>All Loaded Deliveries</h4>
          <p>
            Inspect delivery status, HTTP response codes, and attempts.
          </p>
        </div>

        <span className="live-badge">
          {loading ? 'LOADING' : `${deliveries.length} LOADED`}
        </span>
      </div>

      {retryMessage && (
        <div className="api-error" role="status">
          {retryMessage}
        </div>
      )}

      {loading ? (
        <div className="empty-state">
          <h5>Loading deliveries…</h5>
        </div>
      ) : deliveries.length === 0 ? (
        <div className="empty-state">
          <h5>No deliveries available</h5>
        </div>
      ) : (
        <DeliveryTable
          deliveries={deliveries}
          onRetry={onRetry}
          retryingId={retryingId}
        />
      )}
    </section>
  );
}

// Reusable delivery table
function DeliveryTable({
  deliveries,
  onRetry,
  retryingId,
}) {
  return (
    <div className="table-responsive">
      <table className="table table-dark table-hover align-middle mt-4">
        <thead>
          <tr>
            <th>ID</th>
            <th>Event ID</th>
            <th>Webhook ID</th>
            <th>Status</th>
            <th>HTTP Code</th>
            <th>Attempts</th>
            {onRetry && <th>Action</th>}
          </tr>
        </thead>

        <tbody>
          {deliveries.map((delivery) => (
            <tr key={delivery.id}>
              <td>{delivery.id}</td>
              <td>{delivery.event_id}</td>
              <td>{delivery.webhook_id}</td>

              <td>
                <span
                  className={`delivery-status ${delivery.status}`}
                >
                  {delivery.status.replace('_', ' ')}
                </span>
              </td>

              <td>{delivery.last_response_code ?? '—'}</td>

              <td>
                {delivery.total_attempts ?? delivery.attempts ?? 0}
              </td>

              {onRetry && (
                <td>
                  {delivery.status === 'dead_letter' ? (
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-warning"
                      disabled={retryingId !== null}
                      onClick={() => onRetry(delivery.id)}
                    >
                      {retryingId === delivery.id
                        ? 'Retrying…'
                        : 'Retry'}
                    </button>
                  ) : (
                    <span className="text-secondary">—</span>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Webhooks page
function WebhooksPage({ webhooks, loading, error }) {
  return (
    <section className="content-panel">
      <div className="panel-header">
        <div>
          <h4>Registered Webhooks</h4>
          <p>Inspect your registered delivery endpoints.</p>
        </div>

        <span className="live-badge">
          {loading ? 'LOADING' : `${webhooks.length} REGISTERED`}
        </span>
      </div>

      {error && (
        <div className="api-error" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <div className="empty-state">
          <h5>Loading webhooks…</h5>
        </div>
      ) : webhooks.length === 0 ? (
        <div className="empty-state">
          <h5>No webhooks registered</h5>
          <p>Register a webhook to see it listed here.</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="table table-dark table-hover align-middle mt-4">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Target URL</th>
                <th>Created At</th>
              </tr>
            </thead>

            <tbody>
              {webhooks.map((webhook) => (
                <tr key={webhook.id}>
                  <td>{webhook.id}</td>
                  <td>{webhook.name}</td>

                  <td>
                    <a
                      href={webhook.target_url}
                      target="_blank"
                      rel="noreferrer"
                      className="webhook-url"
                    >
                      {webhook.target_url}
                    </a>
                  </td>

                  <td>
                    {webhook.created_at
                      ? new Date(webhook.created_at).toLocaleString()
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

// Events page
function EventsPage({ events, loading, error }) {
  return (
    <section className="content-panel">
      <div className="panel-header">
        <div>
          <h4>Event History</h4>
          <p>Inspect events stored in your database.</p>
        </div>

        <span className="live-badge">
          {loading ? 'LOADING' : `${events.length} EVENTS`}
        </span>
      </div>

      {error && (
        <div className="api-error" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <div className="empty-state">
          <h5>Loading events…</h5>
        </div>
      ) : events.length === 0 ? (
        <div className="empty-state">
          <h5>No events found</h5>
          <p>Create an event using your API to see it here.</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="table table-dark table-hover align-middle mt-4">
            <thead>
              <tr>
                <th>ID</th>
                <th>Event Type</th>
                <th>Payload</th>
                <th>Status</th>
                <th>Created At</th>
              </tr>
            </thead>

            <tbody>
              {events.map((event) => (
                <tr key={event.id}>
                  <td>{event.id}</td>
                  <td>{event.event_type}</td>

                  <td>
                    <code className="event-payload">
                      {JSON.stringify(event.payload)}
                    </code>
                  </td>

                  <td>
                    <span
                      className={`delivery-status ${event.status}`}
                    >
                      {event.status}
                    </span>
                  </td>

                  <td>
                    {event.created_at
                      ? new Date(event.created_at).toLocaleString()
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default App;
