// src/components/DashboardWidget.js
import './DashboardWidget.css'; // Crie este arquivo CSS depois

const DashboardWidget = ({ title, children }) => {
  return (
    <div className="dashboard-widget">
      {title && <h2 className="widget-title">{title}</h2>}
      <div className="widget-content">
        {children}
      </div>
    </div>
  );
};

export default DashboardWidget;