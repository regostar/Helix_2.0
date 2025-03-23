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
  MenuItem,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import AccessTimeIcon from '@mui/icons-material/AccessTime';

function Workspace({ sequence, onSequenceUpdate }) {
  const [openDialog, setOpenDialog] = useState(false);
  const [editingStep, setEditingStep] = useState(null);
  const [newStep, setNewStep] = useState({
    type: 'email',
    content: '',
    delay: 0,
  });

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
    });
  };

  const handleSaveStep = () => {
    if (!newStep.content) return;

    const updatedSequence = editingStep
      ? sequence.map((step) =>
          step.id === editingStep.id
            ? { ...newStep, id: step.id }
            : step
        )
      : [...sequence, { ...newStep, id: Date.now().toString() }];

    onSequenceUpdate(updatedSequence);
    handleCloseDialog();
  };

  const handleDeleteStep = (id) => {
    onSequenceUpdate(sequence.filter((step) => step.id !== id));
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

        <List>
          {sequence.map((step, index) => (
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
                  secondary={step.content}
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
              {index < sequence.length - 1 && <Divider />}
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