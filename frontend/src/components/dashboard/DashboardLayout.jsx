function DashboardLayout({ sidebar, main, utility }) {
  return (
    <div className="dashboard-shell grid grid-cols-1 items-start gap-6 py-6 lg:gap-8 md:grid-cols-[280px_minmax(0,1fr)] xl:grid-cols-[280px_minmax(0,1fr)_320px]">
      {sidebar}
      <main className="space-y-8" aria-label="Main dashboard content">
        {main}
      </main>
      <div className="md:col-span-2 xl:col-span-1">
        {utility}
      </div>
    </div>
  );
}

export default DashboardLayout;
