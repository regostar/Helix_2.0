import React, { useState, useEffect } from 'react';
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
  MenuItem,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import SequenceDisplay from './SequenceDisplay';

function Workspace({ sequence, onSequenceUpdate }) {
  const [openDialog, setOpenDialog] = useState(false);
  const [editingStep, setEditingStep] = useState(null);
  const [parsedSequence, setParsedSequence] = useState(null);
  const [newStep, setNewStep] = useState({
    type: 'email',
    content: '',
    delay: 0,
    personalization_tips: '',
  });

  useEffect(() => {
    // Parse the sequence if it's a string
    if (typeof sequence === 'string') {
      try {
        const parsed = JSON.parse(sequence);
        if (parsed.tool_result) {
          setParsedSequence(JSON.parse(parsed.tool_result));
        }
      } catch (e) {
        console.error('Error parsing sequence:', e);
      }
    } else {
      setParsedSequence(sequence);
    }
  }, [sequence]);

  const handleOpenDialog = (step) => {
    if (step) {
      setEditingStep(step);
      setNewStep(step);
    } else {
      setEditingStep(null);
      setNewStep({
        type: 'email',
        content: '',
        delay: 0,
        personalization_tips: '',
      });
    }
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingStep(null);
    setNewStep({
      type: 'email',
      content: '',
      delay: 0,
      personalization_tips: '',
    });
  };

  const handleSaveStep = () => {
    if (!newStep.content) return;

    const updatedSteps = editingStep
      ? parsedSequence.steps.map((step) =>
          step.id === editingStep.id
            ? { ...newStep, id: step.id }
            : step
        )
      : [...(parsedSequence?.steps || []), { ...newStep, id: Date.now().toString() }];

    const updatedSequence = {
      ...parsedSequence,
      steps: updatedSteps,
    };

    onSequenceUpdate(updatedSequence);
    handleCloseDialog();
  };

  return (
    <Box sx={{ flexGrow: 1, p: 3, overflow: 'auto' }}>
      <Paper sx={{ height: '100%', p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
          <Typography variant="h5">Recruiting Sequence</Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            Add Step
          </Button>
        </Box>

        {parsedSequence && <SequenceDisplay sequence={parsedSequence} />}
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
            >
              <MenuItem value="email">Email</MenuItem>
              <MenuItem value="linkedin">LinkedIn Message</MenuItem>
              <MenuItem value="call">Phone Call</MenuItem>
              <MenuItem value="meeting">Meeting</MenuItem>
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
              value={newStep.personalization_tips}
              onChange={(e) =>
                setNewStep({ ...newStep, personalization_tips: e.target.value })
              }
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSaveStep} variant="contained" color="primary">
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Workspace; 