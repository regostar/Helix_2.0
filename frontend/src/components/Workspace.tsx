import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  TextField,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Chip,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import AccessTimeIcon from '@mui/icons-material/AccessTime';

interface SequenceStep {
  id: string;
  type: string;
  content: string;
  delay: number;
  personalization_tips?: string;
}

interface SequenceMetadata {
  role: string;
  industry: string;
  seniority: string;
  company_type: string;
  generated_at: string;
}

interface Sequence {
  metadata: SequenceMetadata;
  steps: SequenceStep[];
}

interface WorkspaceProps {
  sequence: Sequence | null;
  onSequenceUpdate: (steps: SequenceStep[]) => void;
}

const Workspace: React.FC<WorkspaceProps> = ({ sequence, onSequenceUpdate }) => {
  const [openDialog, setOpenDialog] = useState(false);
  const [editingStep, setEditingStep] = useState<SequenceStep | null>(null);
  const [newStep, setNewStep] = useState<SequenceStep>({
    id: Date.now().toString(),
    type: 'email',
    content: '',
    delay: 0,
    personalization_tips: ''
  });

  const handleOpenDialog = (step?: SequenceStep) => {
    if (step) {
      setEditingStep(step);
      setNewStep(step);
    } else {
      setEditingStep(null);
      setNewStep({
        id: Date.now().toString(),
        type: 'email',
        content: '',
        delay: 0,
        personalization_tips: ''
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingStep(null);
    setNewStep({
      id: Date.now().toString(),
      type: 'email',
      content: '',
      delay: 0,
      personalization_tips: ''
    });
  };

  const handleSaveStep = () => {
    if (!newStep.content || !sequence) return;

    const updatedSteps = editingStep
      ? sequence.steps.map((step) =>
          step.id === editingStep.id
            ? { ...step, ...newStep }
            : step
        )
      : [...sequence.steps, { ...newStep, id: Date.now().toString() }];

    onSequenceUpdate(updatedSteps);
    handleCloseDialog();
  };

  const handleDeleteStep = (id: string) => {
    if (!sequence) return;
    onSequenceUpdate(sequence.steps.filter((step) => step.id !== id));
  };

  if (!sequence) {
    return (
      <Box sx={{ flexGrow: 1, p: 3, overflow: 'auto' }}>
        <Paper sx={{ height: '100%', p: 3, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            No sequence generated yet. Start a conversation to create one.
          </Typography>
        </Paper>
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1, p: 3, overflow: 'auto' }}>
      <Paper sx={{ height: '100%', p: 3 }}>
        {/* Metadata Section */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h5" gutterBottom>Recruiting Sequence</Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
            <Chip label={`Role: ${sequence.metadata.role}`} color="primary" />
            <Chip label={`Industry: ${sequence.metadata.industry}`} />
            <Chip label={`Seniority: ${sequence.metadata.seniority}`} />
            <Chip label={`Company: ${sequence.metadata.company_type}`} />
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Add Step
          </Button>
        </Box>

        <List>
          {sequence.steps.map((step, index) => (
            <React.Fragment key={step.id}>
              <ListItem>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1">
                        Step {index + 1}: {step.type}
                      </Typography>
                      {step.delay > 0 && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <AccessTimeIcon fontSize="small" />
                          <Typography variant="caption">
                            {step.delay} days
                          </Typography>
                        </Box>
                      )}
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Typography variant="body2">{step.content}</Typography>
                      {step.personalization_tips && (
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                          Personalization Tips: {step.personalization_tips}
                        </Typography>
                      )}
                    </Box>
                  }
                />
                <ListItemSecondaryAction>
                  <IconButton
                    edge="end"
                    onClick={() => handleOpenDialog(step)}
                    sx={{ mr: 1 }}
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    edge="end"
                    onClick={() => handleDeleteStep(step.id)}
                  >
                    <DeleteIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
              {index < sequence.steps.length - 1 && <Divider />}
            </React.Fragment>
          ))}
        </List>
      </Paper>

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingStep ? 'Edit Step' : 'Add New Step'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              select
              label="Type"
              value={newStep.type}
              onChange={(e) => setNewStep({ ...newStep, type: e.target.value })}
              fullWidth
              SelectProps={{
                native: true,
              }}
            >
              <option value="email">Email</option>
              <option value="linkedin">LinkedIn Message</option>
              <option value="call">Phone Call</option>
              <option value="meeting">Meeting</option>
            </TextField>
            <TextField
              label="Content"
              multiline
              rows={4}
              value={newStep.content}
              onChange={(e) => setNewStep({ ...newStep, content: e.target.value })}
              fullWidth
            />
            <TextField
              label="Delay (days)"
              type="number"
              value={newStep.delay}
              onChange={(e) =>
                setNewStep({ ...newStep, delay: parseInt(e.target.value) || 0 })
              }
              fullWidth
            />
            <TextField
              label="Personalization Tips"
              multiline
              rows={2}
              value={newStep.personalization_tips || ''}
              onChange={(e) =>
                setNewStep({ ...newStep, personalization_tips: e.target.value })
              }
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSaveStep} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Workspace; 