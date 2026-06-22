const stages = [
  "intake",  "draft",
  "testing",
  "docs_review",
  "approval"
];

const Workflow = ({ status }: { status: string }) => {
  return (
    <div>
      <h3>Validation Workflow</h3>

      <div style={{ display: "flex", gap: "10px" }}>
        {stages.map((stage) => (
          <div
            key={stage}
            style={{
              padding: "10px",
              border: "1px solid",
              background: stage === status ? "lightgreen" : "#eee"
            }}
          >
            {stage}
          </div>
        ))}
      </div>
    </div>
  );
};

export default Workflow;
